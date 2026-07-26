"""Classify a transcript sentence into Fireflies' insight categories.

Fireflies exposes ``ai_filters`` on every sentence and counts them under
``analytics.categories`` as questions / date-times / metrics / tasks. Those four
categories are exactly the filter pills above the transcript, so this module is
what makes those pills work.

It is deliberately a rule engine, not a model. Three reasons: it runs in
microseconds at ingestion, it produces identical output on every machine (so the
seed data and the deployed demo always agree), and every decision it makes can
be pointed at in an interview and justified.

The same task detection is reused by ``summarizer`` to extract action items, so
a sentence flagged as a task in the transcript is the same sentence that becomes
a task in the summary panel — one source of truth, two features.
"""

from __future__ import annotations

import re

# --- Tasks ------------------------------------------------------------------
# Cues are split by strength, because "I'll send the report on Thursday" and
# "let's get started" are not the same speech act even though both look like
# commitments to a naive keyword match.
#
# STRONG cues name an actor taking on work. They stand alone.
#
# REQUEST cues are questions in *form* but assignments in *function* — "Can you
# put together the migration plan?" is an action item despite the question mark,
# so these are checked before the question gate rather than after it.
TASK_CUES_REQUEST: tuple[str, ...] = (
    "can you ",
    "could you ",
    "would you ",
    "will you ",
    "are you able to",
    "do you mind",
)

TASK_CUES_STRONG: tuple[str, ...] = (
    "action item",
    "i'll ",
    "i will ",
    "we'll ",
    "we will ",
    "i can have",
    "follow up",
    "follow-up",
    "circle back",
    "take care of",
    "make sure",
    "pick this up",
    "put together",
    "send over",
    "write up",
    "sync with",
    "loop in",
    "assign",
    "to-do",
    "todo",
)

# WEAK cues describe work that ought to happen without saying who or when.
# They only count as a task when paired with a date or deadline.
TASK_CUES_WEAK: tuple[str, ...] = (
    "let's ",
    "lets ",
    "need to ",
    "needs to ",
    "have to ",
    "has to ",
    "going to ",
    "should ",
    "please ",
    "set up ",
    "own this",
)

# Phrases that carry a commitment cue but are not commitments to do work.
# Two categories, both principled rather than tuned to any transcript:
#   - hedges and hypotheticals ("we'll see")
#   - speech-act framing, where the "I'll" governs how the speaker is about to
#     talk rather than any deliverable ("I'll be honest", "I'll push back")
TASK_NEGATIONS: tuple[str, ...] = (
    "we'll see",
    "let's say",
    "if we need to",
    "we don't need to",
    "no need to",
    "i'll be honest",
    "i'll be straight",
    "i'll be clear",
    "i'll be blunt",
    "i'll be upfront",
    "i'll say",
    "i'll tell you",
    "i'll admit",
    "i'll push back",
    "i'll let",
    "i'll leave",
    "i'll take us",
    "i'll keep this",
)

# A real action item names something to be done. Fewer content words than this
# and the sentence is procedural noise, not a deliverable.
_MIN_CONTENT_WORDS = 3

# Function words carry no deliverable, so they do not count towards the above.
_FUNCTION_WORDS: frozenset[str] = frozenset(
    """a an the and or but so then that this these those there here it its it's
    i you he she we they me him her us them my your his our their to of in on at
    by for with from as is are was were be been being do does did done have has
    had will would can could should shall may might must not no yes yeah okay ok
    just now well right sure very really quite about into out up down over under
    again more most some any all one two three thing things let lets i'll we'll
    you'll i'd we'd that's what's""".split()
)

# --- Metrics ----------------------------------------------------------------
METRIC_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\d+(\.\d+)?\s*%"),  # 42%, 3.5 %
    re.compile(r"[$€£₹]\s*\d"),  # $40k
    re.compile(r"\b\d+(\.\d+)?\s*(k|m|bn|b)\b", re.I),  # 40k, 1.2m
    re.compile(r"\b(arr|mrr|nps|cac|ltv|roi|churn|conversion|revenue|margin)\b", re.I),
    re.compile(r"\b\d+(\.\d+)?\s*x\b", re.I),  # 3x
    re.compile(r"\b\d{3,}\b"),  # any number of 3+ digits
    re.compile(r"\b(percent|percentage|basis points)\b", re.I),
)

# --- Dates and times --------------------------------------------------------
DATE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", re.I
    ),
    re.compile(
        r"\b(january|february|march|april|may|june|july|august|september|october"
        r"|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)\b",
        re.I,
    ),
    re.compile(r"\b(today|tomorrow|yesterday|tonight|this week|next week|last week)\b", re.I),
    re.compile(r"\b(this|next|last)\s+(month|quarter|sprint|year)\b", re.I),
    re.compile(r"\bq[1-4]\b", re.I),
    re.compile(r"\b\d{1,2}[:.]\d{2}\s*(am|pm)?\b", re.I),
    re.compile(r"\b\d{1,2}\s*(am|pm)\b", re.I),
    re.compile(r"\b\d{1,2}[/-]\d{1,2}([/-]\d{2,4})?\b"),
    re.compile(r"\b(eod|eow|asap|deadline|due date)\b", re.I),
)

# --- Questions --------------------------------------------------------------
QUESTION_OPENERS: tuple[str, ...] = (
    "what", "why", "how", "when", "where", "who", "which", "whose",
    "is", "are", "was", "were", "do", "does", "did", "can", "could",
    "should", "would", "will", "have", "has", "any", "anyone",
)

# --- Sentiment --------------------------------------------------------------
# A small lexicon, not a model. Named honestly for what it is.
POSITIVE_WORDS: frozenset[str] = frozenset(
    """great good excellent awesome perfect love happy excited win winning strong
    solid nice thanks thank appreciate agree agreed yes definitely absolutely
    fantastic impressive improved improvement growth success successful smooth
    clean ready confident glad pleased""".split()
)
NEGATIVE_WORDS: frozenset[str] = frozenset(
    """bad worse worst problem problems issue issues bug bugs broken fail failed
    failing failure blocked blocker risk risky concern concerned concerns worried
    worry difficult hard struggle struggling delay delayed behind slip slipped
    missed miss confusing frustrated frustrating unfortunately no not can't
    cannot won't wrong disappointed churn""".split()
)

_WORD_RE = re.compile(r"[a-z']+")


def _matches_any(patterns: tuple[re.Pattern[str], ...], text: str) -> bool:
    return any(pattern.search(text) for pattern in patterns)


def is_task(text: str) -> bool:
    """True when the sentence reads like somebody committing to do work.

    Three gates, in order of how cheaply they reject:

    1. Hedges and speech-act framing are stripped out (see TASK_NEGATIONS).
    2. A question is a request for information, not a commitment — "Do we need
       to fix that?" is not an action item even though it contains "need to".
       The exception is a *directed request*: "Can you put together the plan?"
       is grammatically a question and functionally an assignment, so request
       cues are checked before the question gate.
    3. A strong cue stands on its own. A weak cue needs a date or deadline
       attached, because "we need to fix onboarding" is an opinion until
       somebody says when.

    Finally the sentence has to name enough substance to be a deliverable —
    "let's get started" clears every cue test and is still not a task.
    """
    lowered = f" {text.lower().strip()} "
    if any(negation in lowered for negation in TASK_NEGATIONS):
        return False

    request = any(cue in lowered for cue in TASK_CUES_REQUEST)
    if not request and is_question(text):
        return False

    strong = request or any(cue in lowered for cue in TASK_CUES_STRONG)
    weak = any(cue in lowered for cue in TASK_CUES_WEAK)
    if not (strong or weak):
        return False

    content_words = [
        word for word in _WORD_RE.findall(lowered) if word not in _FUNCTION_WORDS
    ]
    if len(content_words) < _MIN_CONTENT_WORDS:
        return False

    return strong or is_date_time(text)


def is_question(text: str) -> bool:
    stripped = text.strip()
    if stripped.endswith("?"):
        return True
    first_word = stripped.lower().split(" ", 1)[0].strip(",.;:")
    return first_word in QUESTION_OPENERS and len(stripped.split()) > 3


def is_metric(text: str) -> bool:
    return _matches_any(METRIC_PATTERNS, text)


def is_date_time(text: str) -> bool:
    return _matches_any(DATE_PATTERNS, text)


def detect_sentiment(text: str) -> str:
    """Lexicon sentiment: count hits on each side and take the winner.

    Ties and empty matches fall through to neutral, which is the honest answer
    for most of a transcript.
    """
    words = set(_WORD_RE.findall(text.lower()))
    positive = len(words & POSITIVE_WORDS)
    negative = len(words & NEGATIVE_WORDS)
    if positive > negative:
        return "positive"
    if negative > positive:
        return "negative"
    return "neutral"


def tag(text: str) -> dict[str, object]:
    """Return every insight flag for one sentence, ready to splat onto the model."""
    return {
        "is_task": is_task(text),
        "is_question": is_question(text),
        "is_metric": is_metric(text),
        "is_date_time": is_date_time(text),
        "sentiment": detect_sentiment(text),
    }
