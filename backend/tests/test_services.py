"""Unit tests for the two services that carry the real logic.

Neither of these touches the database, which is the point of keeping the
summariser and the parser free of ORM objects.
"""

import json

import pytest

from app.services import insight_tagger
from app.services.summarizer import HeuristicSummarizer, SentenceInput
from app.services.transcript_parser import TranscriptParseError, parse_transcript


class TestTranscriptParser:
    def test_parses_speaker_prefixed_text(self):
        sentences = parse_transcript("Alice: Hello there.\nBob: Hi Alice.")
        assert [s.speaker_name for s in sentences] == ["Alice", "Bob"]
        assert sentences[0].text == "Hello there."

    def test_parses_bracketed_timestamps(self):
        sentences = parse_transcript("[00:01:30] Alice: We start now.")
        assert sentences[0].start_ms == 90_000
        assert sentences[0].speaker_name == "Alice"

    def test_parses_webvtt(self):
        vtt = (
            "WEBVTT\n\n"
            "00:00:00.000 --> 00:00:04.000\n<v Alice>Opening remarks.\n\n"
            "00:00:04.000 --> 00:00:08.500\nBob: Thanks Alice.\n"
        )
        sentences = parse_transcript(vtt, "meeting.vtt")
        assert len(sentences) == 2
        assert sentences[1].speaker_name == "Bob"
        assert sentences[1].end_ms == 8_500

    def test_parses_srt(self):
        srt = "1\n00:00:02,000 --> 00:00:05,000\nAlice: Subtitle line.\n"
        sentences = parse_transcript(srt, "meeting.srt")
        assert sentences[0].start_ms == 2_000

    def test_parses_fireflies_shaped_json(self):
        payload = json.dumps(
            {
                "sentences": [
                    {"index": 0, "text": "First line.", "speaker_name": "Alice", "start_time": 0},
                    {"index": 1, "text": "Second line.", "speaker_name": "Bob", "start_time": 5.5},
                ]
            }
        )
        sentences = parse_transcript(payload, "meeting.json")
        assert sentences[1].start_ms == 5_500

    def test_does_not_mistake_a_mid_sentence_colon_for_a_speaker(self):
        sentences = parse_transcript("The plan is simple: ship it on Friday.")
        assert sentences[0].speaker_name is None

    def test_synthesises_timings_and_never_moves_backwards(self):
        sentences = parse_transcript("Alice: One two three.\nBob: Four five six.")
        assert sentences[0].start_ms == 0
        assert sentences[0].end_ms > 0
        # A change of speaker costs more silence than a continuation.
        assert sentences[1].start_ms > sentences[0].end_ms

    def test_empty_input_is_a_user_error_not_a_crash(self):
        with pytest.raises(TranscriptParseError):
            parse_transcript("   ")

    def test_malformed_json_reports_a_readable_message(self):
        with pytest.raises(TranscriptParseError):
            parse_transcript("{not json", "x.json")


class TestInsightTagger:
    @pytest.mark.parametrize(
        "text",
        [
            "I'll send the pricing deck over on Thursday.",
            "Can you put together the migration plan?",
            "That's an action item for the platform team.",
        ],
    )
    def test_detects_real_commitments(self, text):
        assert insight_tagger.is_task(text) is True

    @pytest.mark.parametrize(
        "text",
        [
            "Morning everyone, let's get started.",  # weak cue, no deadline
            "Standup, let's keep it tight.",
            "Do we need to fix that before launch?",  # a question, not a task
            "I'll be honest, the numbers are soft.",  # speech act, not a deliverable
            "We'll see how it lands.",
        ],
    )
    def test_rejects_things_that_only_look_like_commitments(self, text):
        assert insight_tagger.is_task(text) is False

    def test_weak_cue_becomes_a_task_once_a_deadline_is_attached(self):
        assert insight_tagger.is_task("We need to refactor the parser.") is False
        assert insight_tagger.is_task("We need to refactor the parser by Friday.") is True

    def test_detects_metrics_questions_and_dates(self):
        assert insight_tagger.is_metric("Revenue grew 42% to $1.4m.") is True
        assert insight_tagger.is_question("What drove the change?") is True
        assert insight_tagger.is_date_time("Let's revisit on Tuesday.") is True

    def test_sentiment_is_a_lexicon_vote(self):
        assert insight_tagger.detect_sentiment("This is a great, solid result.") == "positive"
        assert insight_tagger.detect_sentiment("The rollout failed and users are blocked.") == "negative"
        assert insight_tagger.detect_sentiment("The meeting is at three.") == "neutral"


class TestHeuristicSummarizer:
    def _transcript(self) -> list[SentenceInput]:
        lines = [
            ("Maya", "Let's review the onboarding funnel and then the mobile beta."),
            ("Ravi", "Activation improved from 31% to 38% over the last four weeks."),
            ("Ravi", "The sample workspace is the main driver of that activation change."),
            ("Maya", "Is that causal or just correlated with motivated users?"),
            ("Ravi", "It is correlational, so I'll set up a proper split test this week."),
            ("Dan", "The mobile beta is blocked on offline handling for recordings."),
            ("Dan", "Offline recording needs a write-ahead buffer before any beta ships."),
            ("Maya", "Agreed, the mobile beta waits until offline recording is safe."),
            ("Dan", "I'll wire up crash reporting for the mobile beta by Thursday."),
        ]
        return [
            SentenceInput(idx=i, text=text, start_ms=i * 5000, end_ms=i * 5000 + 4000, speaker_name=who)
            for i, (who, text) in enumerate(lines)
        ]

    def test_produces_every_panel(self):
        draft = HeuristicSummarizer().summarize(self._transcript())
        assert draft.gist
        assert draft.overview
        assert draft.bullet_gist
        assert draft.keywords
        assert draft.chapters
        assert draft.generated_by == "heuristic"

    def test_is_deterministic(self):
        transcript = self._transcript()
        first = HeuristicSummarizer().summarize(transcript)
        second = HeuristicSummarizer().summarize(transcript)
        assert first.gist == second.gist
        assert first.keywords == second.keywords
        assert [c.title for c in first.chapters] == [c.title for c in second.chapters]

    def test_extracts_only_genuine_action_items(self):
        draft = HeuristicSummarizer().summarize(self._transcript())
        texts = " ".join(item.text for item in draft.action_items)
        assert "crash reporting" in texts
        assert "Let's review the onboarding funnel" not in texts

    def test_chapter_titles_are_clean_words(self):
        draft = HeuristicSummarizer().summarize(self._transcript())
        for chapter in draft.chapters:
            # "That'S & White" was a real bug: str.title() mangles apostrophes.
            assert "'" not in chapter.title
            assert chapter.title == chapter.title.strip()

    def test_empty_transcript_returns_an_empty_draft_rather_than_raising(self):
        draft = HeuristicSummarizer().summarize([])
        assert draft.gist == ""
        assert draft.chapters == []
