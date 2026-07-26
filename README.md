# Fireflies.ai Clone — Meeting Notes & Transcription Platform

A functional clone of the Fireflies.ai meeting workspace: a searchable library of
meetings, an interactive transcript with speaker labels and timestamps wired to a
media player, generated summaries, chapters and action items, and full CRUD over
all of it.

Real speech-to-text is out of scope, as the brief allows. Transcripts are seeded
or uploaded (`.txt`, `.vtt`, `.srt`, `.json`); everything downstream — speaker
identification, insight tagging, summaries, chapters and action items — is
derived from them on the server.

| | |
|---|---|
| **Live demo** | _add your Vercel URL here_ |
| **API** | _add your Render URL here_ · interactive docs at `/docs` |

---

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Frontend | Next.js 16 (App Router), TypeScript, Tailwind v4 | Required by the brief |
| Data layer | TanStack Query v5 | Cache, optimistic updates, request dedup |
| UI primitives | Radix UI + `lucide-react` + `sonner` | Accessible dialogs/menus without hand-rolling focus management |
| Backend | FastAPI, Pydantic v2, SQLAlchemy 2.0 (typed) | Required by the brief; OpenAPI comes free |
| Database | SQLite + **FTS5** full-text index | Required by the brief; FTS5 makes search ranked rather than a scan |
| Tests | pytest + `TestClient` | 62 tests over the API and the two core services |

No language model is used anywhere. Summaries are produced by a deterministic
extractive algorithm — see [Summarisation](#summarisation).

---

## Running it locally

Two terminals. Python 3.11+ and Node 20+.

### Backend

```bash
cd backend
python -m venv .venv
```

```bash
.venv\Scripts\activate    # Windows.  macOS/Linux: source .venv/bin/activate
```

```bash
pip install -r requirements.txt
```

```bash
uvicorn app.main:app --reload --port 8000
```

On first start the app creates the schema, builds the FTS5 index and seeds seven
demo meetings. Open <http://localhost:8000/docs> for the interactive API.

To wipe and reseed at any point:

```bash
python -m scripts.reset_db
```

### Frontend

```bash
cd frontend
npm install
```

```bash
cp .env.example .env.local
```

```bash
npm run dev
```

Open <http://localhost:3000>.

### Tests and checks

```bash
cd backend && python -m pytest
```

```bash
cd frontend && npm run typecheck
```

`next build` type-checks as part of the build, so `typecheck` is there for
running the check on its own without a full build.

---

## Architecture

```
fireflies-clone/
├── backend/
│   ├── app/
│   │   ├── main.py            App factory; startup creates tables → FTS index → seed
│   │   ├── core/              Settings (pydantic-settings), engine, session dependency
│   │   ├── models/            SQLAlchemy 2.0 models, grouped by aggregate
│   │   ├── schemas/           Pydantic request/response models
│   │   ├── api/v1/            Routers: meetings, transcript, summaries, action items, search
│   │   ├── services/          The logic: parsing, tagging, summarising, searching
│   │   └── db/                FTS5 setup, seed loader, seed transcripts
│   └── tests/                 API tests + unit tests for the services
└── frontend/src/
    ├── app/                   App Router pages
    ├── components/            layout · meetings · transcript · player · summary · ui
    ├── hooks/                 Queries, mutations, debounce, query-param
    └── lib/                   API client, types, formatters
```

**Request flow.** A route handler validates input with Pydantic, calls a service
for anything non-trivial, and serialises the result. Services take and return
plain data — the summariser and the parser never touch the ORM, which is why
both are unit-testable without a database.

**Ingestion pipeline.** Uploading a transcript and seeding a demo meeting run
the *same* code path (`services/meeting_service.build_meeting`):

```
raw text → transcript_parser → insight_tagger → speakers/participants
                                              → summarizer → summary + chapters + action items
```

So the seed data is a continuous test of the upload path. If the demo meetings
look right, upload works.

---

## Database schema

Field names deliberately mirror Fireflies' own public GraphQL schema
(`Transcript`, `Sentence`, `Summary`), so the model reads as domain-informed
rather than invented.

```
users ──1:N──> meetings ──1:N──> participants
                   │      ──1:N──> speakers ──1:N──> sentences
                   │      ──1:N──> sentences
                   │      ──1:N──> chapters
                   │      ──1:N──> action_items ──N:1──> participants (assignee, nullable)
                   │                            ──N:1──> sentences   (source, nullable)
                   │      ──1:1──> summaries
                   └──N:M──> tags   (via meeting_tags)

sentences_fts  ← FTS5 virtual table shadowing sentences.text
```

| Table | Notable columns |
|---|---|
| `users` | `name`, `email` (unique), `timezone` — the single seeded workspace user |
| `meetings` | `title`, `date`, `duration_seconds`, `meeting_type`, `calendar_type`, `audio_url`, `is_live` |
| `participants` | `email`, `name`, `is_fireflies_user` — unique per `(meeting_id, email)` |
| `speakers` | `speaker_index`, `name`, `color_key` — unique per `(meeting_id, speaker_index)` |
| `sentences` | `idx`, `text`, `start_ms`, `end_ms`, `sentiment`, `is_task`, `is_question`, `is_metric`, `is_date_time` |
| `summaries` | `gist`, `short_summary`, `overview`, `bullet_gist`, `keywords`, `topics_discussed`, `generated_by` |
| `chapters` | `idx`, `title`, `gist`, `start_ms`, `end_ms` |
| `action_items` | `text`, `status`, `source`, `due_date`, `order_index`, `completed_at` |
| `tags` | `name` (unique), `color` |

Decisions worth calling out:

- **Participants and speakers are separate tables.** A participant is invited
  (identified by email); a speaker is a voice in the transcript (identified by a
  name). They usually overlap but not always — a guest can attend and never
  speak. Fireflies models them separately for the same reason.
- **`sentences.start_ms` / `end_ms` are integers, not formatted strings.** The
  player compares them on every animation frame; parsing `"00:01:23"` sixty
  times a second would be absurd.
- **The four boolean columns on `sentences`** are computed once at ingestion and
  drive the transcript filter pills. The same detector feeds action-item
  extraction — one source of truth, two features.
- **`action_items.source`** distinguishes `extracted` from `manual`.
  Regenerating a summary rebuilds the extracted tasks and leaves anything the
  user typed completely alone.
- **`summaries` is a separate 1:1 table**, not columns on `meetings`: the text is
  large, the library list never needs it, and regenerating shouldn't touch the
  meeting row.
- **`ON DELETE CASCADE` throughout**, with `PRAGMA foreign_keys=ON` set on every
  connection in `core/db.py`. SQLite ignores foreign keys by default, so without
  that pragma every cascade in the schema would be decorative.

No migration tool. The schema is small and `scripts/reset_db.py` recreates it;
adding Alembic later is a drop-in.

---

## API overview

Base path `/api/v1`. Full interactive documentation at `/docs`.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/me` | The signed-in user |
| `GET` | `/analytics/overview` | Dashboard counts |
| `GET` | `/meetings` | List; filter by `q`, `participant`, `tag`, `date_from`, `date_to`; `sort`; paginated |
| `POST` | `/meetings` | Create, optionally with a pasted transcript |
| `GET` | `/meetings/{id}` | Detail: speakers, participants, summary, chapters, tags |
| `PATCH` | `/meetings/{id}` | Update title, type, participants, tags |
| `DELETE` | `/meetings/{id}` | Delete, cascading to all children |
| `POST` | `/meetings/{id}/upload-transcript` | Replace the transcript from a file |
| `GET` | `/meetings/{id}/transcript` | Sentences; filter by `q`, `insight`, `speaker_id` |
| `PATCH` | `/meetings/{id}/sentences/{sid}` | Correct a line (re-indexed automatically) |
| `GET` | `/meetings/{id}/summary` | Summary |
| `POST` | `/meetings/{id}/summary/regenerate` | Re-run the summariser |
| `GET`/`POST` | `/meetings/{id}/action-items` | List / create |
| `PATCH`/`DELETE` | `/action-items/{id}` | Update / delete |
| `GET` | `/search` | Cross-meeting full-text search |
| `GET` | `/health` | Liveness, and whether FTS5 is active |

Every list endpoint returns the same envelope — `{items, total, page, page_size}`
— and errors are normalised to `{detail, code}` by exception handlers on the app.

---

## Things worth a closer look

### Full-text search (FTS5)

`LIKE '%term%'` cannot use an index, cannot rank, and cannot tell you where the
match was. The search index is a **FTS5 external-content virtual table** over
`sentences`, kept in sync by three triggers, giving `bm25()` relevance ranking
and `snippet()` excerpts with the hit already marked. Prototyped against a copy
of the seed data it turns a full scan into an index lookup.

User input is tokenised and re-quoted before it reaches `MATCH`, because FTS5
takes a *query language*, not a string — a stray `"` or the bare word `OR` would
otherwise turn the search box into a 500. There is a test asserting exactly
that. If FTS5 is missing from the SQLite build, search falls back to `LIKE` and
the API reports `ranked: false` so the UI can be honest about it.

### Summarisation

Extractive and deterministic — no API key, no network call, identical output
every run. TF-IDF over the transcript with each *sentence* as a document:

```
idf(t)   = log((N + 1) / (df(t) + 1)) + 1
score(s) = Σ tfidf(t, s) / sqrt(|s|)     … adjusted for position and content
```

Dividing by `sqrt(|s|)` stops long rambling sentences winning on volume.
Chapters come from topic-shift detection: slide a window across the transcript,
measure cosine similarity between what was just said and what comes next, and
cut where it dips furthest below its own mean. Thresholds derive from the
transcript's own statistics, not fixed constants.

`Summarizer` is a one-method Protocol, so an LLM-backed implementation is a drop
-in replacement.

### The player

There is no audio, so rather than fake the seek bar, `PlayerProvider` exposes one
interface satisfied two ways: a real `<audio>` element when a meeting has an
`audio_url`, and a `requestAnimationFrame` clock when it does not. Nothing
downstream knows which — click-to-seek, the active-line highlight and the
progress bar work identically either way.

The synthetic clock is anchored to wall time (`anchor.media + elapsed × rate`)
rather than accumulating per-frame deltas, which avoids drift and stays correct
when the browser suspends animation frames for a hidden tab. The active line is
found by binary search over start times — it runs every frame, and a linear scan
of a 400-line transcript at 60fps is 24,000 comparisons a second.

### Timezones

Timestamps are stored in UTC and rendered in the **workspace** timezone from the
user profile, not the browser's. Otherwise a 10am standup reads as 04:30 to one
person and 23:00 to another, and "Today" flips depending on who opens the page.

---

## Assumptions

- **No authentication.** The app runs as a single seeded user, which the brief
  permits. Every route takes its identity from one dependency
  (`api/deps.get_current_user`), so adding real sessions means changing one
  function.
- **No real transcription.** Transcripts are seeded or uploaded.
- **Summaries are algorithmic, not model-generated,** and the UI says so under
  the Overview panel rather than implying otherwise.
- **Seeded dates are relative to now**, so the library always looks like a live
  workspace rather than a snapshot from whenever the repo was cloned.
- **Mocked surfaces**, each with its own page explaining what it would do and
  what already exists to support it: live capture, AskFred, Soundbites,
  Channels, AI Apps, Analytics detail, Integrations, Team, Settings.

---

## Deployment

### Backend → Render

The repo contains `render.yaml`; point Render at it as a Blueprint, or create a
web service manually with:

- Root directory `backend`
- Build `pip install -r requirements.txt`
- Start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Env: `CORS_ORIGINS=https://<your-app>.vercel.app`

A `Dockerfile` is included for hosts that expect a container.

> **Known limitation, stated rather than hidden.** Render's free tier has no
> persistent disk, so the SQLite file is recreated on every deploy or cold start
> and the demo meetings are reseeded automatically. Data an evaluator creates
> survives their session but not a restart. The first request after a spin-down
> takes roughly 50 seconds to wake the instance, which is why the library ships
> a real skeleton state rather than a blank screen. Moving to a host with a
> mounted volume is a config change, not a code change — `DATABASE_URL` already
> points wherever you tell it.

### Frontend → Vercel

Import the repo, set the root directory to `frontend`, and add one environment
variable:

```
NEXT_PUBLIC_API_BASE_URL=https://<your-api>.onrender.com
```

Redeploy the backend afterwards with `CORS_ORIGINS` set to the Vercel URL.
