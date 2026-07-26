"""Parse an uploaded or pasted transcript into sentences.

Four formats are supported — ``.vtt``, ``.srt``, ``.json`` and plain ``.txt`` —
behind one function. Each format gets a small parser and they are registered in
a dict keyed by extension, so supporting a fifth format means writing one
function and adding one line. Nothing else in the app knows or cares which
format a transcript arrived in.

Timings are optional at parse time. Anything missing is synthesised afterwards
at a natural speaking rate, which is what makes a bare wall-of-text paste still
produce a seekable, clickable transcript instead of a dead one.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

# Assumed speaking pace, used only when the source carries no timings.
WORDS_PER_MINUTE = 130
# Silence between two lines from the same speaker: a breath.
_INTRA_TURN_GAP_MS = 300
# Silence when the floor changes hands. Turn-taking in real conversation costs
# close to a second once you include the pause before someone starts talking.
_TURN_CHANGE_GAP_MS = 900
_MIN_SENTENCE_MS = 900

# Matches HH:MM:SS.mmm, HH:MM:SS,mmm, MM:SS and friends.
_TIME_RE = re.compile(r"(?:(\d{1,3}):)?(\d{1,2}):(\d{2})(?:[.,](\d{1,3}))?")
_CUE_RANGE_RE = re.compile(
    r"(?P<start>[\d:.,]+)\s*-->\s*(?P<end>[\d:.,]+)"
)
# WebVTT voice span: <v Alice>text</v>
_VOICE_RE = re.compile(r"<v\s+([^>]+)>(.*?)(?:</v>)?$", re.I | re.S)
# "Alice:" / "Alice Smith:" at the start of a line — but not a mid-sentence colon.
_SPEAKER_PREFIX_RE = re.compile(r"^\s*([A-Z][\w.'\-]*(?:\s+[A-Z][\w.'\-]*){0,3})\s*:\s+(.*)$")
# "[00:01:23] Alice: text" and "Alice (00:01:23): text"
_BRACKET_TIME_RE = re.compile(r"^\s*[\[(]\s*([\d:.,]+)\s*[\])]\s*(.*)$")
_TRAILING_TIME_RE = re.compile(r"^\s*(.+?)\s*[\[(]\s*([\d:.,]+)\s*[\])]\s*:\s*(.*)$")
_TAG_RE = re.compile(r"<[^>]+>")


class TranscriptParseError(ValueError):
    """Raised when a file cannot be read as any supported transcript format."""


@dataclass
class ParsedSentence:
    text: str
    speaker_name: str | None = None
    start_ms: int | None = None
    end_ms: int | None = None


def _timestamp_to_ms(value: str) -> int | None:
    match = _TIME_RE.search(value.strip())
    if not match:
        return None
    hours, minutes, seconds, fraction = match.groups()
    total = int(minutes) * 60_000 + int(seconds) * 1_000
    if hours:
        total += int(hours) * 3_600_000
    if fraction:
        total += int(fraction.ljust(3, "0"))
    return total


def _split_speaker(line: str) -> tuple[str | None, str]:
    """Pull a leading ``Name:`` off a line, if there is one.

    Guarded so a normal sentence containing a colon ("The plan is simple: ship
    it") is not mistaken for a speaker label.
    """
    voice = _VOICE_RE.match(line.strip())
    if voice:
        return voice.group(1).strip(), _TAG_RE.sub("", voice.group(2)).strip()

    match = _SPEAKER_PREFIX_RE.match(line)
    if match:
        candidate, remainder = match.group(1).strip(), match.group(2).strip()
        if len(candidate) <= 40 and remainder:
            return candidate, remainder
    return None, line.strip()


# --- format parsers ---------------------------------------------------------


def _parse_cues(content: str) -> list[ParsedSentence]:
    """Shared parser for WebVTT and SubRip.

    The two formats differ only in the decimal separator and a header line, so
    one implementation covers both rather than duplicating the block-splitting
    logic twice.
    """
    sentences: list[ParsedSentence] = []
    blocks = re.split(r"\n\s*\n", content.replace("\r\n", "\n").strip())

    for block in blocks:
        lines = [line for line in block.split("\n") if line.strip()]
        if not lines:
            continue
        if lines[0].strip().upper().startswith("WEBVTT"):
            lines = lines[1:]
            if not lines:
                continue

        range_match = None
        range_line = 0
        for i, line in enumerate(lines):
            range_match = _CUE_RANGE_RE.search(line)
            if range_match:
                range_line = i
                break
        if not range_match:
            continue

        start_ms = _timestamp_to_ms(range_match.group("start"))
        end_ms = _timestamp_to_ms(range_match.group("end"))
        body = " ".join(lines[range_line + 1 :]).strip()
        if not body:
            continue

        speaker, text = _split_speaker(body)
        text = _TAG_RE.sub("", text).strip()
        if text:
            sentences.append(
                ParsedSentence(text=text, speaker_name=speaker, start_ms=start_ms, end_ms=end_ms)
            )

    if not sentences:
        raise TranscriptParseError("No timed cues found in the subtitle file.")
    return sentences


def _parse_json(content: str) -> list[ParsedSentence]:
    """Accept Fireflies' own sentence shape, a bare list, or Whisper segments."""
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise TranscriptParseError(f"Invalid JSON: {exc.msg}") from exc

    if isinstance(payload, dict):
        rows = payload.get("sentences") or payload.get("segments") or payload.get("transcript")
    else:
        rows = payload

    if not isinstance(rows, list) or not rows:
        raise TranscriptParseError(
            "Expected a list of sentences, or an object with a 'sentences' or 'segments' key."
        )

    def read_time(row: dict, *keys: str) -> int | None:
        for key in keys:
            if key not in row or row[key] is None:
                continue
            value = row[key]
            if isinstance(value, (int, float)):
                # Whisper reports seconds; Fireflies reports seconds too.
                return int(float(value) * 1000)
            parsed = _timestamp_to_ms(str(value))
            if parsed is not None:
                return parsed
        return None

    sentences: list[ParsedSentence] = []
    for row in rows:
        if isinstance(row, str):
            speaker, text = _split_speaker(row)
            if text:
                sentences.append(ParsedSentence(text=text, speaker_name=speaker))
            continue
        if not isinstance(row, dict):
            continue
        text = str(row.get("text") or row.get("raw_text") or "").strip()
        if not text:
            continue
        sentences.append(
            ParsedSentence(
                text=text,
                speaker_name=(row.get("speaker_name") or row.get("speaker") or None),
                start_ms=read_time(row, "start_time", "start", "start_ms"),
                end_ms=read_time(row, "end_time", "end", "end_ms"),
            )
        )

    if not sentences:
        raise TranscriptParseError("The JSON contained no readable sentences.")
    return sentences


def _parse_text(content: str) -> list[ParsedSentence]:
    """Plain text, in whatever shape a human pasted it.

    Handles ``[00:01:23] Alice: …``, ``Alice (00:01:23): …``, ``Alice: …`` and
    unlabelled prose. Prose with no line structure is split into sentences so
    the transcript is still navigable line by line.
    """
    raw_lines = [line for line in content.replace("\r\n", "\n").split("\n") if line.strip()]
    if not raw_lines:
        raise TranscriptParseError("The transcript is empty.")

    sentences: list[ParsedSentence] = []
    for line in raw_lines:
        start_ms: int | None = None

        trailing = _TRAILING_TIME_RE.match(line)
        if trailing:
            speaker = trailing.group(1).strip()
            start_ms = _timestamp_to_ms(trailing.group(2))
            text = trailing.group(3).strip()
            if text:
                sentences.append(
                    ParsedSentence(text=text, speaker_name=speaker or None, start_ms=start_ms)
                )
            continue

        bracket = _BRACKET_TIME_RE.match(line)
        if bracket:
            start_ms = _timestamp_to_ms(bracket.group(1))
            line = bracket.group(2)

        speaker, text = _split_speaker(line)
        if text:
            sentences.append(ParsedSentence(text=text, speaker_name=speaker, start_ms=start_ms))

    # A single unbroken paragraph is not a usable transcript — split it up.
    if len(sentences) == 1 and len(sentences[0].text.split()) > 60:
        speaker = sentences[0].speaker_name
        parts = re.split(r"(?<=[.!?])\s+", sentences[0].text)
        sentences = [
            ParsedSentence(text=part.strip(), speaker_name=speaker)
            for part in parts
            if part.strip()
        ]

    if not sentences:
        raise TranscriptParseError("No readable lines found in the transcript.")
    return sentences


# Registry: adding a format means adding one entry here.
PARSERS = {
    ".vtt": _parse_cues,
    ".srt": _parse_cues,
    ".json": _parse_json,
    ".txt": _parse_text,
    ".md": _parse_text,
}


# A JSON array always opens with an object or a string. A transcript line can
# open with "[00:01:30] …", which is emphatically not JSON.
_JSON_ARRAY_RE = re.compile(r"^\[\s*[\{\"\[]")


def _sniff_format(content: str) -> str:
    """Guess the format when there is no filename to go on (a paste)."""
    stripped = content.lstrip()
    if stripped.upper().startswith("WEBVTT"):
        return ".vtt"
    if stripped.startswith("{") or _JSON_ARRAY_RE.match(stripped):
        return ".json"
    if _CUE_RANGE_RE.search(content):
        return ".srt"
    return ".txt"


def fill_missing_timings(
    sentences: list[ParsedSentence], words_per_minute: int = WORDS_PER_MINUTE
) -> list[ParsedSentence]:
    """Give every sentence a start and end, estimating from word count where the
    source gave us nothing. Runs a single forward pass and never lets a
    timestamp move backwards.

    ``words_per_minute`` is the assumed articulation rate — how fast words come
    out while somebody is actually talking, not the average over the meeting. A
    rapid standup genuinely runs near 160 while a deliberate design review sits
    closer to 110. The silence between lines is modelled separately, and costs
    more when the floor changes hands than when one person keeps talking, which
    is what makes the resulting durations land where a real meeting would.
    """
    ms_per_word = int(60_000 / max(words_per_minute, 1))
    cursor = 0
    previous_speaker: str | None = None

    for position, sentence in enumerate(sentences):
        if position:
            same_speaker = (
                previous_speaker is not None and sentence.speaker_name == previous_speaker
            )
            cursor += _INTRA_TURN_GAP_MS if same_speaker else _TURN_CHANGE_GAP_MS

        if sentence.start_ms is None or sentence.start_ms < cursor:
            sentence.start_ms = cursor

        if sentence.end_ms is None or sentence.end_ms <= sentence.start_ms:
            spoken = max(len(sentence.text.split()) * ms_per_word, _MIN_SENTENCE_MS)
            sentence.end_ms = sentence.start_ms + spoken

        cursor = sentence.end_ms
        previous_speaker = sentence.speaker_name

    return sentences


def parse_transcript(
    content: str,
    filename: str | None = None,
    words_per_minute: int = WORDS_PER_MINUTE,
) -> list[ParsedSentence]:
    """Parse `content` into timed sentences.

    The extension picks the parser; if there isn't one (a paste, say), the
    content is sniffed instead. Raises ``TranscriptParseError`` with a message
    fit to show the user.
    """
    if not content or not content.strip():
        raise TranscriptParseError("The transcript is empty.")

    extension = ""
    if filename and "." in filename:
        extension = filename[filename.rfind(".") :].lower()

    parser = PARSERS.get(extension) or PARSERS[_sniff_format(content)]

    try:
        sentences = parser(content)
    except TranscriptParseError:
        raise
    except Exception as exc:  # a malformed file should not surface as a 500
        raise TranscriptParseError(f"Could not read the transcript: {exc}") from exc

    return fill_missing_timings(sentences, words_per_minute)
