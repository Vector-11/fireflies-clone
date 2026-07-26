# Architecture & decision log

The README says *what* this is. This says *why*, in the shape of the questions
an interviewer is likely to ask. Read it before the evaluation.

---

## 1. Why FastAPI and not Django?

The brief allowed either. FastAPI won on three counts:

- **Pydantic v2 does validation and serialisation in the same type**, so the
  request contract, the response contract and the OpenAPI document never drift
  from each other.
- **The API surface here is small and bespoke.** Django's value is the admin,
  the ORM, migrations and auth — and this app has no auth, one user, and a
  schema small enough that `create_all` plus a reset script beats maintaining
  migrations.
- **Automatic OpenAPI at `/docs`** is a deliverable in itself.

What Django would have given me that I gave up: migrations, and a free admin UI
for inspecting data. I judged both to be worth less than the boilerplate saved.

## 2. Why is the schema shaped the way it is?

I modelled it against **Fireflies' own published GraphQL schema** rather than
inventing one, so the field names (`gist`, `bullet_gist`, `shorthand_bullet`,
`topics_discussed`, `ai_filters`) match the product being cloned.

The decisions that took actual thought:

**Participants and speakers are separate tables.** A participant is invited and
identified by email. A speaker is a voice in the transcript, identified only by
a display name. They overlap most of the time, but a guest can attend silently
and a transcript can contain an unmatched "Speaker 3". Merging them would mean
inventing a fake email for every voice — which is exactly the bug I shipped and
then fixed (see §7).

**`summaries` is a 1:1 table, not columns on `meetings`.** The summary text is
large, the library list never reads it, and regenerating a summary shouldn't
touch the meeting row's `updated_at`.

**`action_items.source` (`extracted` | `manual`).** Regenerating a summary has
to rebuild the extracted tasks without destroying anything the user typed. That
is impossible without a column that distinguishes them. There is a test for it.

**Times in integer milliseconds.** The player finds the active line on every
animation frame. Storing `"00:01:23"` would mean parsing sixty times a second.

**Cascades are declared *and* enforced.** SQLite ignores foreign keys unless you
turn them on, so `core/db.py` sets `PRAGMA foreign_keys=ON` on every connection
via a SQLAlchemy `connect` event. Without it, every `ON DELETE CASCADE` in the
schema is decorative and deleting a meeting silently orphans its sentences.
`tests/test_api.py::test_delete_cascades_to_every_child_table` asserts zero
orphans afterwards.

## 3. How does search work, and why not `LIKE`?

`LIKE '%term%'` has three problems: the leading wildcard makes any index
unusable so it is always a full scan, it cannot rank, and it cannot tell you
*where* in the sentence the match was.

The index is a **FTS5 external-content virtual table**:

```sql
CREATE VIRTUAL TABLE sentences_fts USING fts5(
    text, content='sentences', content_rowid='id', tokenize='porter unicode61'
);
```

`content='sentences'` means the text is stored once — the FTS table holds only
the inverted index and reads rows back by rowid. The cost of that is that SQLite
will not keep the two in sync, which is what the three `AFTER INSERT/UPDATE/
DELETE` triggers are for. `porter` gives stemming, so searching "recording"
finds "record".

That buys `bm25()` relevance ranking and `snippet()`, which returns the matching
fragment with the hit already wrapped in a marker.

**The part that matters most:** user input is tokenised and re-quoted before it
reaches `MATCH`. FTS5 takes a *query language*, not a string — `"`, `*`, `(` and
the bare word `OR` are all syntax. Passing raw input through turns a search box
into a 500, or worse. `db/fts.to_match_expression` splits on word characters and
re-quotes each token; the last token gets a `*` so type-ahead matches prefixes.
`test_fts5_syntax_characters_in_user_input_do_not_break_the_query` fires six
hostile inputs at it.

**If asked "what would you do at 10× the data?"** — the same answer I'd give for
real: this stays fine well beyond this dataset, and the migration path is to a
dedicated search service. The reason I didn't reach for one now is that it adds
a network hop, a sync pipeline, and a second system that can be *silently out of
date*, which is worse than one that is down. Search lives behind one module, so
replacing it is one file.

## 4. How are summaries generated without a language model?

Deterministically, on the server. TF-IDF extractive summarisation, treating the
whole transcript as the corpus and each **sentence** as a document:

```
idf(t)   = log((N + 1) / (df(t) + 1)) + 1
score(s) = Σ tfidf(t, s) / sqrt(|s|)
```

`sqrt(|s|)` normalisation stops a long rambling sentence winning purely on
volume. Scores are then adjusted: the outer 15% of the transcript gets a lift
(openings state purpose, closings state next steps), sentences containing
metrics or commitments get a lift, bare questions get a penalty, and very short
back-channel lines ("sounds good") are damped.

**Chapters** come from topic-shift detection. Slide a window across the
transcript, take the cosine similarity between the bag of words just before each
candidate boundary and the bag just after, and cut where similarity dips
furthest below its own `mean - 0.5σ`. Every threshold is derived from that
transcript's own statistics, so a tightly focused meeting yields few chapters
and a wide-ranging one yields more — no constant tuned to a particular meeting.

**Why not just call an LLM?** For this assignment it is strictly worse: it needs
a key the demo can't ship, it can fail on quota in front of an evaluator, and
the output changes between runs so the seed data and production drift apart.
`Summarizer` is a one-method Protocol precisely so an `LLMSummarizer` is a
drop-in — the interface is the thing that makes that claim true rather than
aspirational.

## 5. Action items and the insight pills

`services/insight_tagger` classifies each sentence into Fireflies' four
categories — task, question, metric, date/time — plus a lexicon sentiment. The
results are stored as boolean columns at ingestion, so the filter pills are an
indexed query rather than a regex sweep on every keystroke.

Task detection is the interesting one, because the naive version is bad. Three
gates:

1. **A question is not a commitment** — "Do we need to fix that?" contains
   "need to" and is not an action item. *Except* directed requests: "Can you put
   together the plan?" is grammatically a question and functionally an
   assignment, so request cues are checked before the question gate.
2. **Hedges and speech-act framing are excluded.** "I'll be honest" and "I'll
   push back" are first-person futures that govern how the speaker is about to
   talk, not deliverables.
3. **Strong cues stand alone; weak cues need a deadline.** "I'll send the deck
   Thursday" is a task. "We need to fix onboarding" is an opinion until someone
   says when.

Then a content-word floor, because "let's get started" clears every cue test and
is still not a task.

The same detector feeds both the pills and the extractor, so a line flagged as a
task in the transcript is the same line that becomes a task in the summary.

## 6. Frontend decisions

**Why client-side fetching rather than server components?** This app is
search-, seek- and mutation-driven; almost every view is interactive. Fetching
in the client with TanStack Query gives cache sharing, request dedup and
optimistic updates, and removes an entire class of SSR/CORS/env-var failure
modes. The cost is no server rendering of content — acceptable for a logged-in
workspace tool that would sit behind auth anyway.

**Optimistic updates.** Ticking an action item updates the cache before the
request goes out and rolls back from a snapshot on failure. Anything else feels
broken over a slow connection.

**The player.** Rather than a decorative seek bar, `PlayerProvider` exposes one
interface backed *either* by a real `<audio>` element or by a
`requestAnimationFrame` clock. The clock is anchored to wall time
(`anchor.media + (now - anchor.wall) × rate`) instead of summing per-frame
deltas — deltas accrue drift, and browsers suspend animation frames entirely for
hidden tabs, so a delta-summing clock silently pauses and resumes minutes
behind. Seeking and rate changes re-anchor.

**Binary search for the active line.** It runs every frame; a linear scan over
400 sentences at 60fps is 24,000 comparisons a second for no reason.

**`TranscriptLine` is memoised** because the parent re-renders on every frame
during playback. Without it, every line re-renders 60 times a second; with it,
only the two whose `isActive` actually changed.

**XSS.** Search snippets arrive from the server containing `<mark>` tags, and
everything around them is user-uploaded transcript text. Rendering that with
`dangerouslySetInnerHTML` would be an injection hole. `splitSnippet` splits on
the markers and returns segments, which React renders as text nodes — a
transcript containing `<script>` is displayed, never executed.

**Timezones.** Stored UTC, rendered in the workspace timezone from the user
profile rather than the browser's. Otherwise "Today" flips depending on who
opens the page.

## 7. Bugs found during the build — and what they teach

Worth knowing, because "tell me about something that went wrong" is a standard
question.

| Bug | Cause | Fix |
|---|---|---|
| Participants duplicated (`SR JW PN SR`) | Speakers were matched to invited participants by email, but a transcript only carries a *name*, so every invited speaker got a second row under a synthesised address | Track names as well as emails when reconciling |
| Meetings displayed at 20:30 and 23:00 | Manifest hours were written as UTC but meant as local wall-clock | Build seed times in the workspace zone, convert to UTC; render in the workspace zone |
| Chapter titles like `"That'S & White"` | `str.title()` uppercases after every non-letter, and contractions weren't stopworded | A `_title_case` that only touches the first letter, plus dropping any token containing an apostrophe |
| Chapter titles picking rare verbs | Plain TF-IDF rewards one-off words | Weight titles by how many *sentences* in the chapter mention a term — a real topic recurs |
| `"Morning everyone, let's get started"` extracted as a task | A single keyword list treated all cues as equal | Strong/weak cue split, question gate, content-word floor (§5) |
| Every write endpoint returned 503 in tests | Seeding demo meetings and creating the workspace user were the same step, so disabling seeding left no user at all | Split `ensure_owner` from `seed_if_empty` — this was a real deployment bug, not just a test problem |
| Detail and search pages rendered blank | `useSearchParams()` put them in a Suspense boundary that never resolved on the client | Read the query string directly; these pages fetch client-side, so the boundary bought nothing |
| Page scrolled instead of the transcript panel | The CSS grid's implicit row is auto-height, so it grew to fit all 63 lines | `grid-rows-[minmax(0,1fr)]` |
| Tests passed individually, failed as a suite | `Base.metadata.drop_all` doesn't drop the FTS5 virtual table, so recycled rowids collided with stale index rows | `fts.drop_fts()`, shared by the test fixture and the reset script |

The last one is the most interesting: it only appears when tests run in
sequence, which is a good argument for the fixture recreating state rather than
assuming it.

## 8. What I'd do next

In priority order, and honestly:

1. **Alembic.** `create_all` is fine for an assignment and wrong for anything
   with real data in it.
2. **Real auth**, replacing `get_current_user`, then scoping every meeting query
   by owner.
3. **A host with a persistent volume**, so the demo database survives a restart.
4. **Pagination or virtualisation for the transcript.** One request for a few
   hundred sentences is correct today; a three-hour meeting would need windowing.
5. **Frontend tests.** There are none. The backend has 62; the player's sync
   logic and the optimistic-update rollback are the two places I'd start,
   because both are stateful enough to break silently.
