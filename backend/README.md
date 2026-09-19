# AgentGate — Milestone 3

AgentGate is a zero-trust runtime security gateway for autonomous AI agents. Milestones 1 and 2 provide the framework-independent security engine, FastAPI API, and in-memory security event log. Milestone 3 adds a deterministic autonomous-agent simulation demonstrating runtime enforcement. It evaluates proposed tool requests; callers must enforce the returned decision before executing a tool. The evaluation endpoint does not execute tools. Scenario runs execute only safe fake tools after ALLOW; an approval workflow is not implemented.

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
- `app/permissions.py`: shared server-owned demo permissions.
- `app/evaluation.py`: shared evaluation and audit operation.
- `app/simulation/`: deterministic scenario definitions, agent, guarded executor, fake tools, and timeline dataclasses.
- `app/api/simulation_routes.py` and `simulation_schemas.py`: scenario HTTP boundary.
- `tests/test_gateway.py`: unchanged core tests.
- `tests/test_api.py` and `tests/test_events.py`: HTTP behavior, isolation, validation, audit storage, and concurrency tests.
- `tests/test_simulation.py`: scenario outcomes, actual adapter execution, audit-before-execution ordering, and API integration.

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

This is Milestone 3 of a larger hackathon project. Frontend, Docker, Azure, GitHub Actions, database persistence, authentication, real LLM integration, and deployment remain outside this milestone.

## Threat model: indirect prompt injection

A customer-support agent receives a trusted user request to find order #4821's tracking information and email it to the customer. An attacker controls a retrieved support document, an **untrusted input**. The document claims to be a system instruction and tells the agent to ignore its task, retrieve 5,000 sensitive customer records, and transfer them externally. This is indirect prompt injection: instructions arrive through outside content rather than through the original user request.

The simulator deliberately models the agent being manipulated. It does not classify text or use a real LLM. The attack script proposes the dangerous action because that is the scenario being demonstrated; it does not parse or execute the document. The note appears as an explicit untrusted timeline step so viewers can see where the attack entered the context.

**AgentGate does not need to perfectly detect whether text is malicious. Instead, it controls what actions the AI agent is actually allowed to perform.** The guard enforces policy at the tool boundary even after the agent has followed an attacker instruction. The two sensitive-data policies independently block the attempted operation; the score of 80 explains risk but does not cause the block.

The demo assumes all proposed actions go through the guard, permissions are server-owned, and action metadata accurately describes the proposed access. This is an application-level simulation, not an OS sandbox or protection against code that bypasses the guard. No real customer data, production tools, or real email is used.

## Deterministic scenarios

| ID | Workflow | Expected outcome |
| --- | --- | --- |
| `normal-support` | `orders/lookup` then `email/send`, using the returned fake tracking number | `SUCCESS`; both ALLOW and execute |
| `prompt-injection` | Untrusted note causes `customer_database/read` of 5,000 sensitive records to `external` | `ATTACK_BLOCKED`; BLOCK, 80, CRITICAL, `executed: false` |
| `destructive-approval` | Trusted request proposes allowlisted `orders/delete` | `APPROVAL_REQUIRED`; REQUIRE_APPROVAL, 25, LOW, `executed: false` |

The fake database returns a small synthetic sample only when allowed. The fake email adapter returns a deterministic message receipt and never sends email. All fake addresses use `example.invalid`. Tool execution is tracked per scenario run and independently checked in tests. UUIDs and UTC timestamps vary; scenario inputs, decisions, risk factors, fake output, and ordering are reproducible.

## Scenario API

Start the server from `backend/`:

```sh
.venv/bin/python -m uvicorn app.main:app --reload
```

Then run:

```sh
curl -sS http://127.0.0.1:8000/api/scenarios
curl -sS -X POST http://127.0.0.1:8000/api/scenarios/normal-support/run
curl -sS -X POST http://127.0.0.1:8000/api/scenarios/prompt-injection/run
curl -sS -X POST http://127.0.0.1:8000/api/scenarios/destructive-approval/run
curl -sS 'http://127.0.0.1:8000/api/events?decision=BLOCK&severity=CRITICAL'
```

`GET /api/scenarios` returns an array of `{id, name, description}`. `POST /api/scenarios/{scenario_id}/run` takes no body and returns `scenario_id`, `scenario_name`, `status`, `summary`, and chronological `steps`. Unknown scenario IDs return 404 without creating events.

Input steps include `input_trust` (`trusted` or `untrusted`) and `input_content`; their decision and event fields are null. Proposed-action steps include tool/action/resource, record count, destination, sensitivity, security decision, policy details, risk, severity, explanation, execution status, `executed`, fake output (only after execution), and an `event_id` linked to the existing `/api/events/{event_id}` endpoint. A context step's `executed: false` simply means it is not a tool invocation.

For the injection scenario, the timeline is:

1. Trusted original support request.
2. Untrusted support document claiming to override the task.
3. Manipulated agent's dangerous proposal, intercepted by AgentGate: `BLOCK`, `80`, `CRITICAL`, `executed: false`, and both `bulk_sensitive_data_export` and `external_sensitive_data_transfer` policy matches.

## Guarded execution architecture

`SimulatedAgent → ToolRequest → GuardedExecutor → evaluate_and_record → existing engine → existing event store → decision → fake tool only for ALLOW`

The agent receives only a guarded executor, not tool adapters. Both the standalone evaluation API and the simulation use the same evaluate-and-audit operation and server-owned permission configuration. Simulation-specific behavior stays outside the core engine. Each run creates fresh fake tools while sharing the application's existing audit store.

The event is saved before inspecting the execution decision. BLOCK returns `BLOCKED`; REQUIRE_APPROVAL returns `PENDING_APPROVAL`; neither invokes the adapter. Audit-write failures also prevent execution. Normal workflows stop if the lookup cannot execute; they do not send a follow-up email. Scenario summaries reflect actual outcomes, with `STOPPED` available if the expected workflow cannot complete.

Existing events describe security evaluations, not tool-completion receipts. Execution outcomes appear in the scenario timeline. Durable logs, actual human approval/resumption, and real tool adapters remain future work. The API metadata remains at version 0.2.0 to preserve the existing Milestone 2 contract.
