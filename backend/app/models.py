"""Typed domain values shared by policies, risk scoring, and the gateway."""

from dataclasses import dataclass
from enum import Enum


class Decision(str, Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"


class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class ToolRequest:
    agent_id: str
    tool: str
    action: str
    resource: str
    record_count: int = 1
    destination: str | None = None
    contains_sensitive_data: bool = False
    reason: str | None = None

    def __post_init__(self) -> None:
        for name in ("agent_id", "tool", "action", "resource"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
        if type(self.record_count) is not int or self.record_count < 0:
            raise ValueError("record_count must be a non-negative integer")
        if type(self.contains_sensitive_data) is not bool:
            raise ValueError("contains_sensitive_data must be a boolean")
        for name in ("destination", "reason"):
            value = getattr(self, name)
            if value is not None and not isinstance(value, str):
                raise ValueError(f"{name} must be a string or None")


@dataclass(frozen=True)
class AgentPermissions:
    agent_id: str
    allowed_tools: set[str]
    allowed_actions: set[str]

    def __post_init__(self) -> None:
        if not isinstance(self.agent_id, str) or not self.agent_id.strip():
            raise ValueError("agent_id must be a non-empty string")
        for name in ("allowed_tools", "allowed_actions"):
            values = getattr(self, name)
            if not isinstance(values, (set, frozenset)) or any(
                not isinstance(value, str) or not value.strip() for value in values
            ):
                raise ValueError(f"{name} must be a set of non-empty strings")
            # Snapshot the caller's allowlists so later mutations cannot change them.
            object.__setattr__(self, name, frozenset(values))


@dataclass(frozen=True)
class PolicyMatch:
    policy_id: str
    decision: Decision
    explanation: str


@dataclass(frozen=True)
class SecurityDecision:
    decision: Decision
    risk_score: int
    severity: Severity
    triggered_policies: tuple[PolicyMatch, ...]
    explanation: str
