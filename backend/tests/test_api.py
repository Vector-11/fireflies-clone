"""End-to-end API tests through the real app, against a temporary database."""

from sqlalchemy import func, select

from app.models import ActionItem, Sentence, Speaker

TRANSCRIPT = (
    "Alice: We need to ship the new billing page by Friday.\n"
    "Bob: I'll take the backend and have it in review by Wednesday.\n"
    "Alice: Revenue is up 12% this quarter so this matters.\n"
    "Bob: Can you send me the spec today?\n"
    "Alice: Yes, I'll send it over this afternoon.\n"
)


def _create_meeting(client, **overrides) -> dict:
    payload = {
        "title": "Billing Sync",
        "transcript": TRANSCRIPT,
        "tags": ["Billing"],
        "meeting_type": "Team Meeting",
        "participants": [{"email": "alice@example.com", "name": "Alice"}],
    }
    payload.update(overrides)
    response = client.post("/api/v1/meetings", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


class TestHealth:
    def test_reports_fts5_availability(self, client):
        body = client.get("/health").json()
        assert body["status"] == "ok"
        # If this is ever False the search tests below are exercising the
        # fallback rather than the thing we actually built.
        assert body["fts5"] is True


class TestMeetingsList:
    def test_returns_the_standard_page_envelope(self, seeded_client):
        body = seeded_client.get("/api/v1/meetings").json()
        assert set(body) == {"items", "total", "page", "page_size"}
        assert body["total"] == 7
        assert len(body["items"]) == 7

    def test_pagination_slices_without_changing_the_total(self, seeded_client):
        body = seeded_client.get("/api/v1/meetings?page=2&page_size=3").json()
        assert body["total"] == 7
        assert len(body["items"]) == 3
        assert body["page"] == 2

    def test_rows_carry_their_aggregate_counts(self, seeded_client):
        row = seeded_client.get("/api/v1/meetings?page_size=1").json()["items"][0]
        assert row["sentence_count"] > 0
        assert row["action_item_count"] >= row["open_action_item_count"]
        assert row["gist"]

    def test_default_sort_is_most_recent_first(self, seeded_client):
        dates = [item["date"] for item in seeded_client.get("/api/v1/meetings").json()["items"]]
        assert dates == sorted(dates, reverse=True)

    def test_sort_oldest_reverses_it(self, seeded_client):
        dates = [
            item["date"]
            for item in seeded_client.get("/api/v1/meetings?sort=oldest").json()["items"]
        ]
        assert dates == sorted(dates)

    def test_filters_by_title(self, seeded_client):
        body = seeded_client.get("/api/v1/meetings?q=standup").json()
        assert body["total"] == 1
        assert "Standup" in body["items"][0]["title"]

    def test_filters_by_participant(self, seeded_client):
        body = seeded_client.get("/api/v1/meetings?participant=sofia").json()
        assert body["total"] >= 1
        for item in body["items"]:
            emails = " ".join(p["email"] for p in item["participants"])
            assert "sofia" in emails.lower()

    def test_filters_by_tag(self, seeded_client):
        body = seeded_client.get("/api/v1/meetings?tag=Sales").json()
        assert body["total"] >= 1
        for item in body["items"]:
            assert "Sales" in [tag["name"] for tag in item["tags"]]

    def test_filters_compose(self, seeded_client):
        both = seeded_client.get("/api/v1/meetings?tag=Engineering&participant=ravi").json()
        assert both["total"] >= 1


class TestMeetingCreate:
    def test_builds_the_whole_meeting_from_a_pasted_transcript(self, client):
        meeting = _create_meeting(client)
        assert {s["name"] for s in meeting["speakers"]} == {"Alice", "Bob"}
        assert meeting["summary"] is not None
        assert meeting["summary"]["generated_by"] == "heuristic"
        assert meeting["chapters"]
        assert meeting["sentence_count"] == 5
        assert meeting["duration_seconds"] > 0

    def test_extracts_action_items_and_assigns_them_to_speakers(self, client):
        meeting = _create_meeting(client)
        items = client.get(f"/api/v1/meetings/{meeting['id']}/action-items").json()
        assert items
        assert all(item["source"] == "extracted" for item in items)
        assert any("backend" in item["text"].lower() for item in items)

    def test_speakers_not_on_the_invite_still_become_participants(self, client):
        meeting = _create_meeting(client)
        emails = {p["email"] for p in meeting["participants"]}
        assert "alice@example.com" in emails  # supplied
        assert any(email.startswith("bob@") for email in emails)  # inferred from transcript

    def test_a_meeting_can_be_created_with_no_transcript(self, client):
        meeting = _create_meeting(client, transcript=None)
        assert meeting["sentence_count"] == 0
        assert meeting["duration_seconds"] == 0

    def test_an_unreadable_transcript_is_a_422_not_a_500(self, client):
        response = client.post(
            "/api/v1/meetings", json={"title": "Broken", "transcript": "{oops", "transcript_filename": "x.json"}
        )
        assert response.status_code == 422
        assert response.json()["detail"]


class TestMeetingUpdateAndDelete:
    def test_patch_only_touches_the_fields_it_is_given(self, client):
        meeting = _create_meeting(client)
        response = client.patch(f"/api/v1/meetings/{meeting['id']}", json={"title": "Renamed"})
        assert response.status_code == 200
        body = response.json()
        assert body["title"] == "Renamed"
        assert body["meeting_type"] == "Team Meeting"  # untouched

    def test_replacing_participants_keeps_existing_rows_and_their_assignments(self, client):
        meeting = _create_meeting(client)
        alice = next(p for p in meeting["participants"] if p["email"] == "alice@example.com")

        item = client.post(
            f"/api/v1/meetings/{meeting['id']}/action-items",
            json={"text": "Own the rollout", "assignee_participant_id": alice["id"]},
        ).json()

        client.patch(
            f"/api/v1/meetings/{meeting['id']}",
            json={"participants": [{"email": "alice@example.com", "name": "Alice Cooper"}]},
        )

        after = client.get(f"/api/v1/meetings/{meeting['id']}/action-items").json()
        still_assigned = next(row for row in after if row["id"] == item["id"])
        # Same participant row, so the assignment survived the sync.
        assert still_assigned["assignee"]["id"] == alice["id"]
        assert still_assigned["assignee"]["name"] == "Alice Cooper"

    def test_delete_cascades_to_every_child_table(self, client, db_session):
        meeting_id = _create_meeting(client)["id"]
        assert client.delete(f"/api/v1/meetings/{meeting_id}").status_code == 204
        assert client.get(f"/api/v1/meetings/{meeting_id}").status_code == 404

        for model in (Sentence, Speaker, ActionItem):
            remaining = db_session.execute(
                select(func.count()).select_from(model).where(model.meeting_id == meeting_id)
            ).scalar_one()
            assert remaining == 0, f"{model.__name__} rows were orphaned"

    def test_unknown_meeting_returns_a_structured_404(self, client):
        response = client.get("/api/v1/meetings/999999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestTranscript:
    def test_returns_every_sentence_in_order(self, client):
        meeting_id = _create_meeting(client)["id"]
        body = client.get(f"/api/v1/meetings/{meeting_id}/transcript").json()
        assert body["total"] == 5
        assert [s["idx"] for s in body["sentences"]] == [0, 1, 2, 3, 4]

    def test_insight_filter_narrows_to_flagged_lines(self, client):
        meeting_id = _create_meeting(client)["id"]
        metrics = client.get(f"/api/v1/meetings/{meeting_id}/transcript?insight=metric").json()
        assert metrics["total"] >= 1
        assert all(s["is_metric"] for s in metrics["sentences"])

    def test_editing_a_line_updates_the_search_index_too(self, client):
        meeting_id = _create_meeting(client)["id"]
        sentence = client.get(f"/api/v1/meetings/{meeting_id}/transcript").json()["sentences"][0]

        client.patch(
            f"/api/v1/meetings/{meeting_id}/sentences/{sentence['id']}",
            json={"text": "We must ship the zephyr dashboard by Friday."},
        )
        # The FTS triggers fire on UPDATE, so the new word is immediately findable.
        found = client.get("/api/v1/search?q=zephyr").json()
        assert found["total_meetings"] == 1

    def test_a_sentence_from_another_meeting_is_a_404(self, client):
        first = _create_meeting(client)["id"]
        second = _create_meeting(client, title="Other")["id"]
        foreign = client.get(f"/api/v1/meetings/{second}/transcript").json()["sentences"][0]
        response = client.patch(
            f"/api/v1/meetings/{first}/sentences/{foreign['id']}", json={"text": "nope"}
        )
        assert response.status_code == 404


class TestActionItems:
    def test_manual_items_survive_a_summary_regeneration(self, client):
        meeting_id = _create_meeting(client)["id"]
        manual = client.post(
            f"/api/v1/meetings/{meeting_id}/action-items", json={"text": "Book the retro"}
        ).json()
        assert manual["source"] == "manual"

        assert client.post(f"/api/v1/meetings/{meeting_id}/summary/regenerate").status_code == 200

        after = client.get(f"/api/v1/meetings/{meeting_id}/action-items").json()
        assert manual["id"] in [row["id"] for row in after]
        # ...while the extracted ones were rebuilt rather than duplicated.
        extracted = [row for row in after if row["source"] == "extracted"]
        assert len(extracted) == len({row["text"] for row in extracted})

    def test_completing_an_item_stamps_completed_at_and_reopening_clears_it(self, client):
        meeting_id = _create_meeting(client)["id"]
        item = client.post(
            f"/api/v1/meetings/{meeting_id}/action-items", json={"text": "Ship it"}
        ).json()
        assert item["completed_at"] is None

        done = client.patch(f"/api/v1/action-items/{item['id']}", json={"status": "completed"}).json()
        assert done["status"] == "completed"
        assert done["completed_at"] is not None

        reopened = client.patch(f"/api/v1/action-items/{item['id']}", json={"status": "open"}).json()
        assert reopened["completed_at"] is None

    def test_an_assignee_must_belong_to_the_meeting(self, client):
        first = _create_meeting(client)
        second = _create_meeting(client, title="Other")
        outsider = second["participants"][0]["id"]

        response = client.post(
            f"/api/v1/meetings/{first['id']}/action-items",
            json={"text": "Cross-meeting assignment", "assignee_participant_id": outsider},
        )
        assert response.status_code == 422

    def test_delete_removes_the_item(self, client):
        meeting_id = _create_meeting(client)["id"]
        item = client.post(
            f"/api/v1/meetings/{meeting_id}/action-items", json={"text": "Temporary"}
        ).json()
        assert client.delete(f"/api/v1/action-items/{item['id']}").status_code == 204
        remaining = client.get(f"/api/v1/meetings/{meeting_id}/action-items").json()
        assert item["id"] not in [row["id"] for row in remaining]


class TestSearch:
    def test_ranks_results_and_marks_the_match(self, seeded_client):
        body = seeded_client.get("/api/v1/search?q=pricing").json()
        assert body["ranked"] is True
        assert body["total_meetings"] >= 1
        assert "<mark>" in body["results"][0]["hits"][0]["snippet"]

    def test_matches_word_prefixes_for_type_ahead(self, seeded_client):
        # "pric" must find "pricing" before the user finishes the word.
        assert seeded_client.get("/api/v1/search?q=pric").json()["total_meetings"] >= 1

    def test_stems_so_recording_matches_record(self, seeded_client):
        assert seeded_client.get("/api/v1/search?q=recordings").json()["total_meetings"] >= 1

    def test_fts5_syntax_characters_in_user_input_do_not_break_the_query(self, seeded_client):
        # Quotes, asterisks and OR are FTS5 syntax. Passing them through raw
        # would turn a search box into a 500.
        for query in ['"unbalanced', "wild*", "a OR b", "NEAR(", "*", '""']:
            response = seeded_client.get("/api/v1/search", params={"q": query})
            assert response.status_code == 200, f"{query!r} broke search"

    def test_also_matches_meeting_titles(self, seeded_client):
        body = seeded_client.get("/api/v1/search?q=investor").json()
        assert any("Investor" in result["title"] for result in body["results"])

    def test_deleting_a_meeting_removes_it_from_the_index(self, client):
        meeting_id = _create_meeting(client, transcript="Alice: The quokka migration is done.")["id"]
        assert client.get("/api/v1/search?q=quokka").json()["total_meetings"] == 1
        client.delete(f"/api/v1/meetings/{meeting_id}")
        assert client.get("/api/v1/search?q=quokka").json()["total_meetings"] == 0


class TestTranscriptUpload:
    def test_uploading_replaces_the_transcript_and_rebuilds_the_summary(self, client):
        meeting_id = _create_meeting(client)["id"]
        vtt = (
            "WEBVTT\n\n"
            "00:00:00.000 --> 00:00:04.000\n<v Carol>Completely different content about kayaks.\n\n"
            "00:00:04.000 --> 00:00:09.000\n<v Dave>I'll order the kayaks by Monday.\n"
        )
        response = client.post(
            f"/api/v1/meetings/{meeting_id}/upload-transcript",
            files={"file": ("notes.vtt", vtt, "text/vtt")},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["sentence_count"] == 2
        assert {s["name"] for s in body["speakers"]} == {"Carol", "Dave"}

        # The old content is gone from the index, the new content is in it.
        # "backend" appeared only in the replaced transcript — searching for
        # "billing" would still hit because the meeting is *titled* "Billing
        # Sync" and title matching is deliberate.
        assert client.get("/api/v1/search?q=backend").json()["total_meetings"] == 0
        assert client.get("/api/v1/search?q=kayaks").json()["total_meetings"] == 1

    def test_an_unparseable_upload_is_rejected_with_a_message(self, client):
        meeting_id = _create_meeting(client)["id"]
        response = client.post(
            f"/api/v1/meetings/{meeting_id}/upload-transcript",
            files={"file": ("broken.json", "{nope", "application/json")},
        )
        assert response.status_code == 422


class TestWorkspace:
    def test_me_returns_the_seeded_user(self, seeded_client):
        body = seeded_client.get("/api/v1/me").json()
        assert body["email"] == "priyanshu@fireflies.demo"

    def test_analytics_overview_adds_up(self, seeded_client):
        body = seeded_client.get("/api/v1/analytics/overview").json()
        assert body["total_meetings"] == 7
        assert body["total_duration_seconds"] > 0
        assert body["unique_participants"] > 0
        assert body["top_tags"]
