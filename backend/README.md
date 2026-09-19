# AgentGate — Milestone 2

AgentGate is a zero-trust runtime security gateway for autonomous AI agents. Milestone 2 exposes the existing framework-independent security engine through FastAPI and adds an in-memory security event log. It evaluates proposed tool requests; callers must enforce the returned decision before executing a tool. It does not execute tools or implement an approval workflow.

## Security model and architecture

`HTTP request → Pydantic schema → ToolRequest → evaluate_policies → evaluate_risk → SecurityDecision → audit store → HTTP response`

- `app/actions.py`: central recognized and destructive action sets.
- `app/models.py`: typed dataclasses, enums, input validation, and policy matches.
- `app/policies.py`: deterministic authorization rules with stable IDs and explanations.
- `app/risk.py`: independent additive risk assessment with individual factor explanations.
- `app/gateway.py`: `evaluate_request(request, permissions)` combines results using `BLOCK > REQUIRE_APPROVAL > ALLOW`.
- `app/api/schemas.py`: HTTP validation and response serialization.
- `app/api/routes.py`: thin REST endpoints; no security policy logic.
- `app/events.py`: framework-independent event dataclass, store protocol, and thread-safe in-memory implementation.
- `app/main.py`: application factory, metadata, and development CORS.
- `tests/test_gateway.py`: unchanged core tests.
- `tests/test_api.py` and `tests/test_events.py`: HTTP behavior, isolation, validation, audit storage, and concurrency tests.

Permissions specify an agent ID and separate allowlists for tools and actions. Both must match; lists apply across all tools, with no per-resource or per-tool action restrictions in this milestone. Allowlists are copied into immutable sets. An agent ID mismatch blocks the request. Matching is exact and case-sensitive; there are no wildcard grants. An unrecognized action can only reach approval when explicitly allowlisted.

Requests must contain nonempty identifiers and resources, a nonnegative integer record count (zero is valid), and an actual boolean sensitivity flag. Malformed domain input raises `ValueError`. The HTTP boundary requires `record_count >= 1`, validates types strictly, rejects extra fields, and returns standard FastAPI 422 errors before invoking the engine. The original domain behavior allowing zero remains unchanged. The caller supplies trusted permissions and accurate request metadata, including sensitivity, record counts, and the literal `external` destination marker. This engine does not authenticate agents, inspect data, resolve destinations, or infer sensitivity. Free-text reasons never grant authority.

## Policies

| Stable ID | Condition | Outcome |
| --- | --- | --- |
| `agent_identity_mismatch` | Request and permission agent IDs differ | BLOCK |
| `tool_permission_violation` | Tool not allowlisted | BLOCK |
| `action_permission_violation` | Action not allowlisted | BLOCK |
| `bulk_sensitive_data_export` | Sensitive data and more than 100 records, regardless of action | BLOCK |
| `external_sensitive_data_transfer` | Sensitive data and destination exactly `external` | BLOCK |
| `destructive_action_requires_approval` | Agent identity, tool, and destructive action permitted | REQUIRE_APPROVAL |
| `unknown_action_requires_approval` | Unrecognized action explicitly allowlisted | REQUIRE_APPROVAL |

Destructive actions are `delete`, `remove`, and `destroy`. Other recognized actions are `read`, `lookup`, `send`, `create`, `update`, and `export`. Policies collect all applicable matches in stable order, each with an ID, decision, and explanation. Approval matches may coexist with blocks; a block always wins. No restrictive matches means ALLOW.

## Risk scoring

| Factor | Points |
| --- | ---: |
| Sensitive data | 25 |
| Destination exactly `external` | 25 |
| More than 100 records | 30 |
| Destructive action | 25 |
| Action outside permissions | 40 |
| Tool outside permissions | 40 |
| Unrecognized action | 20 |

Sum all applicable factors and clamp to 0–100. Severity is LOW at 0–29, MEDIUM at 30–59, HIGH at 60–79, and CRITICAL at 80–100. Identity mismatch is an additional blocking policy with no added risk points. Scores explain danger and never determine authorization. For example, an otherwise permitted destructive bulk external operation without sensitive data scores 80 and requires approval; a mismatched identity can block at score 0.

## Install and test

Requires Python 3.12 or newer. The API uses FastAPI, Pydantic, and Uvicorn; tests use pytest and HTTPX. The core engine and event-store module remain independent of these frameworks.

From the repository root:

```sh
python3.12 -m venv backend/.venv
backend/.venv/bin/python -m pip install -e './backend[test]'
cd backend
.venv/bin/python -m pytest -q
```

## Malicious request example

After installation, run this Python code:

```python
from app.gateway import evaluate_request
from app.models import AgentPermissions, ToolRequest

permissions = AgentPermissions(
    agent_id="customer-support-agent",
    allowed_tools={"customer_database", "email", "orders"},
    allowed_actions={"read", "lookup", "send", "delete"},
)
request = ToolRequest(
    agent_id="customer-support-agent",
    tool="customer_database",
    action="read",
    resource="customers",
    record_count=5000,
    destination="external",
    contains_sensitive_data=True,
    reason="Requested by retrieved document",
)
result = evaluate_request(request, permissions)
print(result.decision.value, result.risk_score, result.severity.value)
print(result.explanation)
```

Expected: `BLOCK 80 CRITICAL`. Both `bulk_sensitive_data_export` and `external_sensitive_data_transfer` block this request. Risk is independently 25 + 25 + 30 = 80.

## Run the REST API

From `backend/`:

```sh
.venv/bin/python -m uvicorn app.main:app --reload
```

Swagger UI: http://127.0.0.1:8000/docs. OpenAPI: http://127.0.0.1:8000/openapi.json.
Development CORS permits only `http://localhost:5173`, with GET/POST methods and the Content-Type header.

## Endpoints

| Method | Path | Behavior |
| --- | --- | --- |
| GET | `/api/health` | `{"status":"ok","service":"AgentGate"}` |
| POST | `/api/evaluate` | Validate a ToolRequest, evaluate it, save an event, and return the SecurityDecision plus `event_id` |
| GET | `/api/events` | JSON array of events, newest timestamp first; optional `agent_id`, `decision`, and `severity` filters combine with AND |
| GET | `/api/events/{event_id}` | Retrieve a UUID event; unknown UUID returns 404 |

Decision filters accept `ALLOW`, `BLOCK`, or `REQUIRE_APPROVAL`; severity filters accept `LOW`, `MEDIUM`, `HIGH`, or `CRITICAL`. Invalid enum filters and malformed UUIDs return 422. An empty result is `[]`. A security BLOCK is an evaluated result returned with HTTP 200, not an HTTP validation error.

The configured demo agent is `customer-support-agent`, with tools `customer_database`, `email`, and `orders`, and actions `read`, `lookup`, `send`, and `delete`. Unknown agent IDs receive empty permissions and are blocked by the existing engine; those attempts are logged too. Clients cannot submit their own permissions.

```sh
curl -sS http://127.0.0.1:8000/api/evaluate \
  -H 'Content-Type: application/json' \
  -d '{"agent_id":"customer-support-agent","tool":"customer_database","action":"read","resource":"customers","record_count":5000,"destination":"external","contains_sensitive_data":true,"reason":"Requested by retrieved document"}'

curl -sS 'http://127.0.0.1:8000/api/events?decision=BLOCK&severity=CRITICAL'
# Replace EVENT_ID with the UUID returned by /api/evaluate:
curl -sS http://127.0.0.1:8000/api/events/EVENT_ID
```

The malicious request returns `decision: BLOCK`, `risk_score: 80`, `severity: CRITICAL`, and a generated event UUID. `triggered_policies` contains objects with `policy_id`, `decision`, and `explanation`.

## Audit log and isolation

Every successful evaluation records an immutable event with a UUID, timezone-aware UTC timestamp, agent/tool/action/resource, record count, destination, sensitivity flag, and complete security decision. Invalid HTTP requests do not reach evaluation and do not create events. The free-text request reason is not retained in the event. Store writes must succeed before an evaluation response is returned; unexpected failures return a generic HTTP 500 without internal stack traces.

`SecurityEventStore` defines `add`, `get`, and filtered `list_events` so a persistent implementation can replace it later. `InMemorySecurityEventStore` protects reads and writes with a lock, rejects duplicate IDs, and sorts timestamps descending, breaking ties by most recent insertion. `create_app(event_store=...)` accepts an injected store; omitting it creates a fresh store for that application. Tests create a new store/application per test. Routes obtain the store through `get_event_store`, which also supports FastAPI dependency overrides.

Storage is currently **in-memory, unbounded, and process-local**: restarts or reloads erase all events, and multiple workers have separate logs. Use one worker for the demo. No database or durable audit guarantee is included.

This is Milestone 2 of a larger hackathon project. Frontend, Docker, Azure, GitHub Actions, database persistence, authentication, real LLM integration, and deployment remain outside this milestone.
