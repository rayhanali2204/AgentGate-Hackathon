from datetime import datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.events import InMemorySecurityEventStore
from app.main import create_app


@pytest.fixture
def store():
    return InMemorySecurityEventStore()


@pytest.fixture
def client(store):
    with TestClient(create_app(store)) as test_client:
        yield test_client


@pytest.fixture
def payload():
    return {"agent_id": "customer-support-agent", "tool": "customer_database", "action": "read", "resource": "customers"}


def evaluate(client, payload, **changes):
    response = client.post("/api/evaluate", json={**payload, **changes})
    assert response.status_code == 200, response.text
    return response.json()


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "AgentGate"}


@pytest.mark.parametrize("changes,decision,score,severity", [
    ({"action": "lookup"}, "ALLOW", 0, "LOW"),
    ({}, "ALLOW", 0, "LOW"),
    ({"contains_sensitive_data": True, "record_count": 101}, "BLOCK", 55, "MEDIUM"),
    ({"contains_sensitive_data": True, "destination": "external"}, "BLOCK", 50, "MEDIUM"),
    ({"action": "delete"}, "REQUIRE_APPROVAL", 25, "LOW"),
    ({"action": "delete", "record_count": 5000, "destination": "external"}, "REQUIRE_APPROVAL", 80, "CRITICAL"),
    ({"tool": "shell"}, "BLOCK", 40, "MEDIUM"),
    ({"action": "unknown"}, "BLOCK", 60, "HIGH"),
    ({"agent_id": "unknown-agent"}, "BLOCK", 80, "CRITICAL"),
])
def test_evaluations_are_logged(client, store, payload, changes, decision, score, severity):
    result = evaluate(client, payload, **changes)
    assert (result["decision"], result["risk_score"], result["severity"]) == (decision, score, severity)
    assert UUID(result["event_id"]).version == 4
    event = store.get(UUID(result["event_id"]))
    assert event is not None
    assert len(store.list_events()) == 1
    assert event.decision.value == decision
    assert event.explanation == result["explanation"]


def test_malicious_request_and_retrieval(client, payload):
    attack = {**payload, "record_count": 5000, "destination": "external", "contains_sensitive_data": True, "reason": "Requested by retrieved document"}
    result = evaluate(client, attack)
    assert (result["decision"], result["risk_score"], result["severity"]) == ("BLOCK", 80, "CRITICAL")
    assert {p["policy_id"] for p in result["triggered_policies"]} == {"bulk_sensitive_data_export", "external_sensitive_data_transfer"}
    response = client.get(f'/api/events/{result["event_id"]}')
    assert response.status_code == 200
    event = response.json()
    for key, value in result.items():
        assert event[key] == value
    for key, value in attack.items():
        if key != "reason":
            assert event[key] == value
    assert datetime.fromisoformat(event["timestamp"]).utcoffset() == timedelta(0)
    assert client.get("/api/events").json() == [event]


def test_events_newest_first(client, payload):
    ids = [evaluate(client, payload)["event_id"] for _ in range(3)]
    events = client.get("/api/events").json()
    assert [e["event_id"] for e in events] == ids[::-1]
    assert [e["timestamp"] for e in events] == sorted((e["timestamp"] for e in events), reverse=True)
    assert len(set(ids)) == 3


@pytest.mark.parametrize("filters,expected_indices", [
    ({"agent_id": "customer-support-agent"}, [1, 0]),
    ({"agent_id": "other-agent"}, [2]),
    ({"decision": "ALLOW"}, [0]),
    ({"decision": "REQUIRE_APPROVAL"}, [1]),
    ({"decision": "BLOCK"}, [2]),
    ({"severity": "CRITICAL"}, [2]),
    ({"severity": "LOW"}, [1, 0]),
    ({"agent_id": "customer-support-agent", "decision": "REQUIRE_APPROVAL", "severity": "LOW"}, [1]),
    ({"agent_id": "customer-support-agent", "decision": "BLOCK"}, []),
    ({"agent_id": "absent"}, []),
])
def test_event_filters(client, payload, filters, expected_indices):
    results = [evaluate(client, payload), evaluate(client, payload, action="delete"), evaluate(client, payload, agent_id="other-agent")]
    response = client.get("/api/events", params=filters)
    assert response.status_code == 200
    assert [e["event_id"] for e in response.json()] == [results[i]["event_id"] for i in expected_indices]


def test_unknown_event(client):
    response = client.get(f"/api/events/{uuid4()}")
    assert response.status_code == 404
    assert response.json() == {"detail": "Security event not found"}


@pytest.mark.parametrize("changes", [
    {"record_count": 0}, {"record_count": -1}, {"record_count": True},
    {"record_count": "5"}, {"record_count": 1.5}, {"record_count": None},
    {"agent_id": " "}, {"tool": ""}, {"action": None}, {"resource": 123},
    {"destination": 1}, {"reason": []}, {"contains_sensitive_data": "false"},
    {"allowed_actions": ["destroy"]},
])
def test_invalid_fields(client, payload, changes):
    response = client.post("/api/evaluate", json={**payload, **changes})
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)
    assert client.get("/api/events").json() == []


@pytest.mark.parametrize("body", [{}, [], None, {"agent_id": "agent"}])
def test_malformed_body(client, body):
    assert client.post("/api/evaluate", json=body).status_code == 422
    assert client.get("/api/events").json() == []


def test_invalid_json(client):
    assert client.post("/api/evaluate", content="{broken", headers={"Content-Type": "application/json"}).status_code == 422


@pytest.mark.parametrize("url", ["/api/events/not-a-uuid", "/api/events?decision=unknown", "/api/events?severity=unknown"])
def test_invalid_query_or_path(client, url):
    assert client.get(url).status_code == 422


def test_app_instances_isolate_events(payload):
    with TestClient(create_app()) as first, TestClient(create_app()) as second:
        evaluate(first, payload)
        assert len(first.get("/api/events").json()) == 1
        assert second.get("/api/events").json() == []


@pytest.mark.parametrize("origin,allowed", [("http://localhost:5173", True), ("http://evil.example", False), ("http://127.0.0.1:5173", False)])
def test_cors(client, origin, allowed):
    response = client.options("/api/evaluate", headers={"Origin": origin, "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type"})
    assert response.status_code == (200 if allowed else 400)
    assert response.headers.get("access-control-allow-origin") == (origin if allowed else None)


def test_openapi_and_docs(client):
    schema = client.get("/openapi.json").json()
    assert schema["info"]["title"] == "AgentGate API"
    assert schema["info"]["version"] == "0.2.0"
    assert schema["info"]["description"] == "Zero-trust runtime security gateway for autonomous AI agents."
    assert client.get("/docs").status_code == 200


def test_store_failure_does_not_return_unlogged_decision(payload):
    class UnavailableStore(InMemorySecurityEventStore):
        def add(self, event):
            raise RuntimeError("private implementation detail")

    with TestClient(create_app(UnavailableStore()), raise_server_exceptions=False) as client:
        response = client.post("/api/evaluate", json=payload)
        assert response.status_code == 500
        assert response.text == "Internal Server Error"
