"""
Tests for triage API: start, answer, result.
"""

from fastapi.testclient import TestClient

# Ordered question_ids in the flow (from state_machine)
QUESTION_IDS = [
    "chief_complaint",
    "duration",
    "severity_self",
    "fever",
    "breathing",
    "chest_pain",
    "consciousness",
    "bleeding",
    "pain_level",
    "other_symptoms",
]


def test_triage_start(client: TestClient) -> None:
    r = client.post("/api/v1/triage/start", json={})
    assert r.status_code == 200
    data = r.json()
    assert "session_id" in data
    assert len(data["session_id"]) > 0
    assert data["triage_state"] == "ongoing"
    assert "first_question" in data
    assert data["first_question"]["question_id"] == "chief_complaint"
    assert len(data["first_question"]["text"]) > 0


def test_triage_answer_session_not_found(client: TestClient) -> None:
    r = client.post(
        "/api/v1/triage/answer",
        json={
            "session_id": "00000000-0000-0000-0000-000000000000",
            "question_id": "chief_complaint",
            "answer": "headache",
        },
    )
    assert r.status_code == 404
    assert "Session not found" in r.json()["detail"]


def test_triage_answer_validation_empty_answer(client: TestClient) -> None:
    # Start a session first
    start_r = client.post("/api/v1/triage/start", json={})
    assert start_r.status_code == 200
    session_id = start_r.json()["session_id"]

    r = client.post(
        "/api/v1/triage/answer",
        json={
            "session_id": session_id,
            "question_id": "chief_complaint",
            "answer": "",  # min_length=1
        },
    )
    assert r.status_code == 422


def test_triage_answer_first_question_returns_ongoing(client: TestClient) -> None:
    start_r = client.post("/api/v1/triage/start", json={})
    assert start_r.status_code == 200
    session_id = start_r.json()["session_id"]

    r = client.post(
        "/api/v1/triage/answer",
        json={
            "session_id": session_id,
            "question_id": "chief_complaint",
            "answer": "I have a headache",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["triage_state"] == "ongoing"
    assert data["next_question"]["question_id"] == "duration"
    assert "progress" in data


def test_triage_full_flow_completed(client: TestClient) -> None:
    """Run through all questions with non-emergency answers until completed."""
    start_r = client.post("/api/v1/triage/start", json={})
    assert start_r.status_code == 200
    session_id = start_r.json()["session_id"]

    answers = [
        "headache and fever",
        "2 days",
        "moderate",
        "no",
        "no",
        "no",
        "no",
        "no",
        "3",
        "no",
    ]
    for qid, answer in zip(QUESTION_IDS, answers):
        r = client.post(
            "/api/v1/triage/answer",
            json={"session_id": session_id, "question_id": qid, "answer": answer},
        )
        assert r.status_code == 200, (qid, r.json())
        data = r.json()
        if data["triage_state"] == "completed":
            assert "severity_level" in data
            assert "recommendation" in data
            break
        assert data["triage_state"] == "ongoing"
        assert "next_question" in data

    # Get result
    result_r = client.get(f"/api/v1/triage/result/{session_id}")
    assert result_r.status_code == 200
    res = result_r.json()
    assert res["status"] == "completed"
    assert res["session_id"] == session_id
    assert res["chief_complaint"] == "headache and fever"
    assert "severity_level" in res
    assert "recommendation" in res


def test_triage_result_not_found(client: TestClient) -> None:
    r = client.get("/api/v1/triage/result/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


def test_triage_result_ongoing_returns_400(client: TestClient) -> None:
    """Result for a session that is still ongoing returns 400."""
    start_r = client.post("/api/v1/triage/start", json={})
    assert start_r.status_code == 200
    session_id = start_r.json()["session_id"]

    r = client.get(f"/api/v1/triage/result/{session_id}")
    assert r.status_code == 400
    assert "not yet complete" in r.json()["detail"].lower()
