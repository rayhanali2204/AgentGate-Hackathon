# AgentGate — Milestone 1

AgentGate is a zero-trust runtime security gateway for autonomous AI agents. This milestone implements only a framework-independent Python security engine. It evaluates proposed tool requests; callers must enforce the returned decision before executing a tool. It does not execute tools or implement an approval workflow.

## Security model and architecture

`ToolRequest → evaluate_policies → evaluate_risk → SecurityDecision`

- `app/actions.py`: central recognized and destructive action sets.
- `app/models.py`: typed dataclasses, enums, input validation, and policy matches.
- `app/policies.py`: deterministic authorization rules with stable IDs and explanations.
- `app/risk.py`: independent additive risk assessment with individual factor explanations.
- `app/gateway.py`: `evaluate_request(request, permissions)` combines results using `BLOCK > REQUIRE_APPROVAL > ALLOW`.
- `tests/test_gateway.py`: policy, scoring, boundary, and validation tests.

Permissions specify an agent ID and separate allowlists for tools and actions. Both must match; lists apply across all tools, with no per-resource or per-tool action restrictions in this milestone. Allowlists are copied into immutable sets. An agent ID mismatch blocks the request. Matching is exact and case-sensitive; there are no wildcard grants. An unrecognized action can only reach approval when explicitly allowlisted.

Requests must contain nonempty identifiers and resources, a nonnegative integer record count (zero is valid), and an actual boolean sensitivity flag. Malformed input raises `ValueError`. The caller supplies trusted permissions and accurate request metadata, including sensitivity, record counts, and the literal `external` destination marker. This engine does not authenticate agents, inspect data, resolve destinations, or infer sensitivity. Free-text reasons never grant authority.

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

Requires Python 3.12 or newer. There are no runtime dependencies; pytest is the test dependency.

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

This is Milestone 1 of a larger hackathon project. Web APIs, dashboards, persistence, authentication, LLM integration, cloud infrastructure, and deployment are intentionally outside this milestone.
