"""The HTTP surface: every AI request returns a response and its record."""

from fastapi.testclient import TestClient


def test_health_reports_stubs_as_stubs(client: TestClient):
    body = client.get("/health").json()

    statuses = {component["name"]: component["status"] for component in body["components"]}
    assert statuses == {"llm": "stub", "memory": "stub", "retrieval": "stub", "cache": "stub"}


def test_chat_returns_a_response_and_an_execution_record(client: TestClient):
    response = client.post("/api/chat", json={"message": "My API is slow again."})

    assert response.status_code == 200
    body = response.json()
    assert body["response"]
    assert body["execution"]["request_id"]
    assert body["execution"]["total_duration_ms"] >= 0
    assert body["execution"]["context"]["sources"]


def test_chat_rejects_an_empty_message(client: TestClient):
    assert client.post("/api/chat", json={"message": ""}).status_code == 422


def test_execution_config_is_echoed_back_on_the_record(client: TestClient):
    body = client.post(
        "/api/chat",
        json={
            "message": "My API is slow again.",
            "config": {"memory_enabled": False, "retrieval_enabled": True, "cache_enabled": False},
        },
    ).json()

    assert body["execution"]["execution_config"] == {
        "memory_enabled": False,
        "retrieval_enabled": True,
        "cache_enabled": False,
    }


def test_history_and_replay_follow_from_a_request(client: TestClient):
    created = client.post("/api/chat", json={"message": "What plan am I currently on?"}).json()
    request_id = created["execution"]["request_id"]

    history = client.get("/api/analytics/history", params={"limit": 5}).json()
    assert history["items"][0]["request_id"] == request_id

    replay = client.get(f"/api/analytics/history/{request_id}").json()
    assert [step["name"] for step in replay["steps"]][0] == "cache lookup"
    assert replay["message"] == "What plan am I currently on?"


def test_replay_of_an_unknown_request_is_a_404(client: TestClient):
    assert client.get("/api/analytics/history/does-not-exist").status_code == 404


def test_history_limit_is_bounded(client: TestClient):
    assert client.get("/api/analytics/history", params={"limit": 0}).status_code == 422
    assert client.get("/api/analytics/history", params={"limit": 500}).status_code == 422


def test_summary_aggregates_recorded_requests(client: TestClient):
    client.post("/api/chat", json={"message": "How do I generate a new API key?"})
    client.post("/api/chat", json={"message": "How do I reset my API key?"})

    summary = client.get("/api/analytics/summary").json()

    assert summary["llm"]["total_requests"] >= 2
    assert summary["cache"]["hits"] >= 1
    assert summary["cost_is_estimated"] is True


def test_compare_runs_the_ladder_of_configurations(client: TestClient):
    body = client.post("/api/chat/compare", json={"message": "My API is slow again."}).json()

    labels = [run["label"] for run in body["runs"]]
    assert labels[0] == "llm only"
    assert len(labels) == 4
    # More context costs more tokens; the comparison must be able to show that.
    token_counts = [run["execution"]["context"]["estimated_tokens"] for run in body["runs"]]
    assert token_counts[0] == 0
    assert token_counts[-1] == max(token_counts)
