"""Deterministic authorization policies; no risk thresholds are used."""

from .actions import DESTRUCTIVE_ACTIONS, RECOGNIZED_ACTIONS
from .models import AgentPermissions, Decision, PolicyMatch, ToolRequest


def evaluate_policies(request: ToolRequest, permissions: AgentPermissions) -> tuple[PolicyMatch, ...]:
    matches: list[PolicyMatch] = []

    def add(policy_id: str, decision: Decision, explanation: str) -> None:
        matches.append(PolicyMatch(policy_id, decision, explanation))

    if request.agent_id != permissions.agent_id:
        add("agent_identity_mismatch", Decision.BLOCK, "Permissions belong to a different agent.")
    tool_allowed = request.tool in permissions.allowed_tools
    action_allowed = request.action in permissions.allowed_actions
    if not tool_allowed:
        add("tool_permission_violation", Decision.BLOCK, f"Tool {request.tool!r} is not allowed.")
    if not action_allowed:
        add("action_permission_violation", Decision.BLOCK, f"Action {request.action!r} is not allowed.")
    if request.contains_sensitive_data and request.record_count > 100:
        add("bulk_sensitive_data_export", Decision.BLOCK, "Sensitive data access exceeds 100 records.")
    if request.contains_sensitive_data and request.destination == "external":
        add("external_sensitive_data_transfer", Decision.BLOCK, "Sensitive data cannot be transferred externally.")
    if tool_allowed and action_allowed and request.agent_id == permissions.agent_id and request.action in DESTRUCTIVE_ACTIONS:
        add("destructive_action_requires_approval", Decision.REQUIRE_APPROVAL, "Permitted destructive actions require approval.")
    if action_allowed and request.action not in RECOGNIZED_ACTIONS:
        add("unknown_action_requires_approval", Decision.REQUIRE_APPROVAL, "Explicitly allowlisted unknown actions require approval.")
    return tuple(matches)
