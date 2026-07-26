"""Turn a transcript into the summary panels the UI renders.

The assignment allows summaries to be seeded, mocked, or LLM-generated. This
implementation is **extractive and deterministic**: no API key, no network call,
no per-request cost, and identical output every time it runs. That matters more
than it sounds — the deployed demo can never break because a quota ran out, and
the seed data on your laptop matches the seed data in production exactly.

The approach is classic TF-IDF extractive summarisation, with the whole
transcript as the corpus and each *sentence* as a document:

    idf(t)   = log((N + 1) / (df(t) + 1)) + 1
    score(s) = Σ tfidf(t, s) / sqrt(|s|)      … then adjusted by position and content

Dividing by sqrt(|s|) stops long rambling sentences from winning on volume
alone. Chapters come from topic-shift detection: slide a window across the
transcript, measure cosine similarity between what was just said and what comes
next, and cut where that similarity dips furthest below its own mean. Every
threshold is derived from the transcript's own statistics rather than tuned to
any particular meeting.

``Summarizer`` is a Protocol with one implementation. That is not
over-abstraction for its own sake: dropping in an ``LLMSummarizer`` later means
writing one class and changing one line in the factory, and the interface is the
thing that makes that true.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Protocol, Sequence

from app.services import insight_tagger

STOPWORDS: frozenset[str] = frozenset(
    """a about above after again against all also am an and any are aren't as at be
    because been before being below between both but by can cannot could couldn't
    did didn't do does doesn't doing don't down during each few for from further had
    hadn't has hasn't have haven't having he her here hers herself him himself his
    how i i'd i'll i'm i've if in into is isn't it it's its itself just let's me more
    most mustn't my myself no nor not of off on once only or other ought our ours
    ourselves out over own same shan't she should shouldn't so some such than that
    the their theirs them themselves then there these they this those through to too
    under until up very was wasn't we were weren't what when where which while who
    whom why with won't would wouldn't you your yours yourself yourselves yeah okay
    ok right well gonna wanna kind sort like really actually basically maybe think
    know going get got go one two three thing things lot bit sure mean means said
    say says talk talking see look looking want need make made take taken come came
    give given put use used using work working time way people
    yes yep nope thanks thank please still much many good great bad better best
    first second third next last new old big small long short high low half every
    another else enough perhaps probably certainly obviously honestly genuinely
    exactly definitely absolutely completely totally quite rather anything nothing
    something everyone anyone nobody somebody everything morning afternoon evening
    week month quarter year day days weeks months years minutes hours
    makes making moved moves moving keeps keeping looks adds adding puts putting
    takes takes comes gets getting goes tells telling asks asking asked thought
    happen happens happening seen seeing feels felt wanted needed needs left
    started starting done gone told heard doing""".split()
)

# Deterministic emoji for the "bullet gist" panel, which Fireflies renders with
# descriptive emojis. First keyword hit wins; order therefore matters.
_EMOJI_RULES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("revenue", "pricing", "price", "budget", "cost", "arr", "mrr", "deal"), "💰"),
    (("hire", "hiring", "candidate", "interview", "recruit", "team"), "👥"),
    (("bug", "issue", "incident", "outage", "broken", "risk", "blocker"), "🐛"),
    (("launch", "ship", "release", "rollout", "deploy"), "🚀"),
    (("customer", "client", "user", "feedback", "churn"), "🧑‍💼"),
    (("deadline", "timeline", "schedule", "sprint", "quarter"), "🗓️"),
    (("design", "ui", "ux", "mockup", "prototype"), "🎨"),
    (("data", "metric", "analytics", "dashboard", "report"), "📊"),
    (("security", "compliance", "privacy", "soc"), "🔒"),
    (("decision", "agreed", "approve", "sign off", "consensus"), "✅"),
)
_DEFAULT_EMOJI = "🔹"

_WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z'\-]+")
# Verbal filler that starts a sentence and adds nothing to a summary line.
_LEADING_FILLER_RE = re.compile(
    r"^(so|and|but|ok|okay|yeah|yep|right|well|um|uh|like|i mean|you know)[,\s]+",
    re.I,
)


@dataclass(frozen=True)
class SentenceInput:
    """Plain input to the summariser.

    Deliberately not an ORM object: this service never touches the database, so
    it can be unit tested with a list of literals.
    """

    idx: int
    text: str
    start_ms: int
    end_ms: int
    speaker_name: str | None = None


@dataclass
class ChapterDraft:
    idx: int
    title: str
    gist: str
    start_ms: int
    end_ms: int


@dataclass
class ActionItemDraft:
    text: str
    sentence_idx: int | None = None
    speaker_name: str | None = None


@dataclass
class SummaryDraft:
    gist: str = ""
    short_summary: str = ""
    overview: str = ""
    bullet_gist: str = ""
    shorthand_bullet: str = ""
    notes: str = ""
    keywords: list[str] = field(default_factory=list)
    topics_discussed: list[str] = field(default_factory=list)
    chapters: list[ChapterDraft] = field(default_factory=list)
    action_items: list[ActionItemDraft] = field(default_factory=list)
    generated_by: str = "heuristic"
    model: str | None = None


class Summarizer(Protocol):
    """One method, so an LLM-backed implementation is a drop-in replacement."""

    def summarize(self, sentences: Sequence[SentenceInput]) -> SummaryDraft: ...


def _tokenize(text: str) -> list[str]:
    """Content words only.

    Anything containing an apostrophe is dropped: in English a contraction is
    almost always a function word ("that's", "we'll", "doesn't"), and letting
    them through produced chapter titles like "That's & Needs". Enumerating
    every contraction as a stopword would be endless; one rule covers them all.
    """
    return [
        word
        for word in (match.group(0).lower() for match in _WORD_RE.finditer(text))
        if len(word) > 2 and "'" not in word and word not in STOPWORDS
    ]


def _title_case(term: str) -> str:
    """Capitalise the first letter only.

    ``str.title()`` uppercases after every non-letter, so "o'brien" becomes
    "O'Brien" — fine — but "that's" becomes "That'S", which is not.
    """
    return term[:1].upper() + term[1:] if term else term


def _clean(text: str) -> str:
    """Strip verbal filler and normalise punctuation for display."""
    cleaned = _LEADING_FILLER_RE.sub("", text.strip())
    cleaned = re.sub(r"\s+", " ", cleaned)
    if not cleaned:
        return ""
    cleaned = cleaned[0].upper() + cleaned[1:]
    if cleaned[-1] not in ".!?":
        cleaned += "."
    return cleaned


def _cosine(a: Counter[str], b: Counter[str]) -> float:
    if not a or not b:
        return 0.0
    shared = set(a) & set(b)
    numerator = sum(a[term] * b[term] for term in shared)
    if not numerator:
        return 0.0
    norm_a = math.sqrt(sum(value * value for value in a.values()))
    norm_b = math.sqrt(sum(value * value for value in b.values()))
    return numerator / (norm_a * norm_b)


def _pick_emoji(text: str) -> str:
    lowered = text.lower()
    for keywords, emoji in _EMOJI_RULES:
        if any(keyword in lowered for keyword in keywords):
            return emoji
    return _DEFAULT_EMOJI


class HeuristicSummarizer:
    """Extractive summariser. See the module docstring for the method."""

    def summarize(self, sentences: Sequence[SentenceInput]) -> SummaryDraft:
        usable = [s for s in sentences if s.text and s.text.strip()]
        if not usable:
            return SummaryDraft()

        tokens = [_tokenize(s.text) for s in usable]
        idf = self._inverse_document_frequency(tokens)
        scores = self._score_sentences(usable, tokens, idf)

        chapters = self._detect_chapters(usable, tokens, idf, scores)
        keywords = self._top_keywords(tokens, idf, limit=10)
        action_items = self._extract_action_items(usable)

        ranked = sorted(range(len(usable)), key=lambda i: scores[i], reverse=True)

        def in_reading_order(count: int) -> list[int]:
            return sorted(ranked[:count])

        gist_idx = ranked[0]
        short_idxs = in_reading_order(min(3, len(usable)))
        overview_idxs = in_reading_order(min(max(5, len(usable) // 8), 10))
        bullet_idxs = in_reading_order(min(5, len(usable)))

        return SummaryDraft(
            gist=_clean(usable[gist_idx].text),
            short_summary=" ".join(_clean(usable[i].text) for i in short_idxs),
            overview=self._build_overview(usable, overview_idxs),
            bullet_gist="\n".join(
                f"{_pick_emoji(usable[i].text)} {_clean(usable[i].text)}" for i in bullet_idxs
            ),
            shorthand_bullet=self._build_shorthand(usable, chapters, scores),
            notes=self._build_notes(usable, chapters, scores),
            keywords=keywords,
            topics_discussed=[chapter.title for chapter in chapters],
            chapters=chapters,
            action_items=action_items,
        )

    # -- scoring -------------------------------------------------------------

    def _inverse_document_frequency(self, tokens: list[list[str]]) -> dict[str, float]:
        total = len(tokens)
        document_frequency: Counter[str] = Counter()
        for sentence_tokens in tokens:
            document_frequency.update(set(sentence_tokens))
        return {
            term: math.log((total + 1) / (count + 1)) + 1.0
            for term, count in document_frequency.items()
        }

    def _score_sentences(
        self,
        sentences: Sequence[SentenceInput],
        tokens: list[list[str]],
        idf: dict[str, float],
    ) -> list[float]:
        total = len(sentences)
        scores: list[float] = []

        for position, (sentence, sentence_tokens) in enumerate(zip(sentences, tokens)):
            if not sentence_tokens:
                scores.append(0.0)
                continue

            counts = Counter(sentence_tokens)
            # Length-normalised so verbosity alone cannot win.
            base = sum(count * idf.get(term, 1.0) for term, count in counts.items())
            score = base / math.sqrt(len(sentence_tokens))

            # Openings state the purpose, closings state the next steps. Both
            # carry more summary value than the middle, so give the outer
            # fifteen percent of the transcript a modest lift.
            relative = position / max(total - 1, 1)
            if relative < 0.15 or relative > 0.85:
                score *= 1.15

            # Concrete numbers and commitments are what people want in a recap.
            if insight_tagger.is_metric(sentence.text):
                score *= 1.20
            if insight_tagger.is_task(sentence.text):
                score *= 1.15
            # A bare question rarely summarises anything on its own.
            if insight_tagger.is_question(sentence.text):
                score *= 0.85
            # Back-channel noise ("mhm", "sounds good") is short by definition.
            if len(sentence_tokens) < 4:
                score *= 0.4

            scores.append(score)

        return scores

    def _top_keywords(
        self, tokens: list[list[str]], idf: dict[str, float], limit: int
    ) -> list[str]:
        weights: Counter[str] = Counter()
        for sentence_tokens in tokens:
            for term, count in Counter(sentence_tokens).items():
                weights[term] += count * idf.get(term, 1.0)
        return [term for term, _ in weights.most_common(limit)]

    # -- chapters ------------------------------------------------------------

    def _detect_chapters(
        self,
        sentences: Sequence[SentenceInput],
        tokens: list[list[str]],
        idf: dict[str, float],
        scores: list[float],
    ) -> list[ChapterDraft]:
        """Cut the transcript where the subject matter actually changes.

        Slide a window over the sentences, compare the bag of words just before
        each candidate boundary with the bag just after, and treat the deepest
        dips in similarity as topic shifts. The cut-off is the series' own
        ``mean - 0.5 * stdev``, so a tightly focused meeting yields few chapters
        and a wide-ranging one yields more, with no fixed magic number.
        """
        total = len(sentences)
        window = max(3, total // 12)
        min_chapter_length = max(4, total // 15)
        max_chapters = max(2, min(8, total // 12))

        if total < window * 2 + 2:
            return [self._build_chapter(0, sentences, tokens, idf, scores, 0, total - 1)]

        similarities: list[tuple[int, float]] = []
        for boundary in range(window, total - window):
            before: Counter[str] = Counter()
            after: Counter[str] = Counter()
            for offset in range(window):
                before.update(tokens[boundary - 1 - offset])
                after.update(tokens[boundary + offset])
            similarities.append((boundary, _cosine(before, after)))

        if not similarities:
            return [self._build_chapter(0, sentences, tokens, idf, scores, 0, total - 1)]

        values = [value for _, value in similarities]
        mean = sum(values) / len(values)
        variance = sum((value - mean) ** 2 for value in values) / len(values)
        cutoff = mean - 0.5 * math.sqrt(variance)

        candidates = sorted(
            (boundary for boundary, value in similarities if value < cutoff),
            key=lambda boundary: dict(similarities)[boundary],
        )

        boundaries: list[int] = []
        for candidate in candidates:
            if len(boundaries) >= max_chapters - 1:
                break
            if all(abs(candidate - chosen) >= min_chapter_length for chosen in boundaries) and (
                candidate >= min_chapter_length and total - candidate >= min_chapter_length
            ):
                boundaries.append(candidate)

        boundaries.sort()
        edges = [0, *boundaries, total]
        return [
            self._build_chapter(i, sentences, tokens, idf, scores, edges[i], edges[i + 1] - 1)
            for i in range(len(edges) - 1)
        ]

    def _build_chapter(
        self,
        idx: int,
        sentences: Sequence[SentenceInput],
        tokens: list[list[str]],
        idf: dict[str, float],
        scores: list[float],
        start: int,
        end: int,
    ) -> ChapterDraft:
        span = range(start, end + 1)

        # Weight by how many *sentences* in the chapter mention a term, not by
        # raw frequency. A genuine topic gets returned to; a rare one-off verb
        # scores highly on plain TF-IDF and produces titles like "White & Page".
        sentence_frequency: Counter[str] = Counter()
        for i in span:
            sentence_frequency.update(set(tokens[i]))

        weights = {
            term: frequency * idf.get(term, 1.0)
            for term, frequency in sentence_frequency.items()
        }
        recurring = {term: weight for term, weight in weights.items() if sentence_frequency[term] > 1}
        # Fall back to every term only when nothing in the chapter recurs.
        pool = recurring or weights

        top_terms = [
            term for term, _ in sorted(pool.items(), key=lambda item: item[1], reverse=True)[:2]
        ]
        title = " & ".join(_title_case(term) for term in top_terms) if top_terms else "Discussion"

        best = max(span, key=lambda i: scores[i])
        return ChapterDraft(
            idx=idx,
            title=title,
            gist=_clean(sentences[best].text),
            start_ms=sentences[start].start_ms,
            end_ms=sentences[end].end_ms,
        )

    # -- action items --------------------------------------------------------

    def _extract_action_items(self, sentences: Sequence[SentenceInput]) -> list[ActionItemDraft]:
        """Every sentence the insight tagger calls a task becomes a candidate.

        Deduplicated on normalised text so a commitment restated three times in
        a row produces one task, and capped so the panel stays readable.
        """
        seen: set[str] = set()
        drafts: list[ActionItemDraft] = []

        for sentence in sentences:
            if not insight_tagger.is_task(sentence.text):
                continue
            text = _clean(sentence.text)
            if len(text.split()) < 4:
                continue
            fingerprint = re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            drafts.append(
                ActionItemDraft(
                    text=text, sentence_idx=sentence.idx, speaker_name=sentence.speaker_name
                )
            )
            if len(drafts) >= 8:
                break

        return drafts

    # -- prose builders ------------------------------------------------------

    def _build_overview(self, sentences: Sequence[SentenceInput], idxs: list[int]) -> str:
        """Group the selected sentences into short paragraphs so the overview
        panel reads as prose rather than a wall of text."""
        lines = [_clean(sentences[i].text) for i in idxs]
        paragraphs = [" ".join(lines[i : i + 3]) for i in range(0, len(lines), 3)]
        return "\n\n".join(paragraph for paragraph in paragraphs if paragraph)

    def _build_shorthand(
        self,
        sentences: Sequence[SentenceInput],
        chapters: list[ChapterDraft],
        scores: list[float],
    ) -> str:
        return "\n".join(f"- {chapter.title}: {chapter.gist}" for chapter in chapters)

    def _build_notes(
        self,
        sentences: Sequence[SentenceInput],
        chapters: list[ChapterDraft],
        scores: list[float],
    ) -> str:
        """Detailed notes: each chapter as a heading with its strongest lines."""
        blocks: list[str] = []
        for chapter in chapters:
            in_chapter = [
                i
                for i, sentence in enumerate(sentences)
                if chapter.start_ms <= sentence.start_ms <= chapter.end_ms
            ]
            if not in_chapter:
                continue
            best = sorted(in_chapter, key=lambda i: scores[i], reverse=True)[:3]
            bullets = "\n".join(f"- {_clean(sentences[i].text)}" for i in sorted(best))
            blocks.append(f"**{chapter.title}**\n{bullets}")
        return "\n\n".join(blocks)


def get_summarizer() -> Summarizer:
    """Single place to swap implementations."""
    return HeuristicSummarizer()
