"""Additive risk factors describe danger without granting authorization."""

from dataclasses import dataclass

from .actions import DESTRUCTIVE_ACTIONS, RECOGNIZED_ACTIONS
from .models import AgentPermissions, Severity, ToolRequest


@dataclass(frozen=True)
class RiskFactor:
    factor_id: str
    points: int
    explanation: str


@dataclass(frozen=True)
class RiskAssessment:
    score: int
    severity: Severity
    factors: tuple[RiskFactor, ...]


def severity_for_score(score: int) -> Severity:
    if type(score) is not int or not 0 <= score <= 100:
        raise ValueError("score must be an integer between 0 and 100")
    if score < 30:
        return Severity.LOW
    if score < 60:
        return Severity.MEDIUM
    if score < 80:
        return Severity.HIGH
    return Severity.CRITICAL


def evaluate_risk(request: ToolRequest, permissions: AgentPermissions) -> RiskAssessment:
    candidates = (
        (request.contains_sensitive_data, "sensitive_data", 25, "Sensitive data"),
        (request.destination == "external", "external_destination", 25, "External destination"),
        (request.record_count > 100, "bulk_records", 30, "More than 100 records"),
        (request.action in DESTRUCTIVE_ACTIONS, "destructive_action", 25, "Destructive action"),
        (request.action not in permissions.allowed_actions, "action_permission", 40, "Action outside permissions"),
        (request.tool not in permissions.allowed_tools, "tool_permission", 40, "Tool outside permissions"),
        (request.action not in RECOGNIZED_ACTIONS, "unknown_action", 20, "Unrecognized action"),
    )
    factors = tuple(RiskFactor(key, points, label) for applies, key, points, label in candidates if applies)
    score = min(100, max(0, sum(factor.points for factor in factors)))
    return RiskAssessment(score, severity_for_score(score), factors)
