"""Framework-independent simulation inputs, execution results, and timeline."""

from dataclasses import dataclass
from enum import Enum
from uuid import UUID

from ..events import SecurityEvent
from ..models import Decision, PolicyMatch, Severity


class InputTrust(str, Enum):
    TRUSTED = "trusted"
    UNTRUSTED = "untrusted"


class ExecutionStatus(str, Enum):
    EXECUTED = "EXECUTED"
    BLOCKED = "BLOCKED"
    PENDING_APPROVAL = "PENDING_APPROVAL"


class ScenarioStatus(str, Enum):
    SUCCESS = "SUCCESS"
    ATTACK_BLOCKED = "ATTACK_BLOCKED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    STOPPED = "STOPPED"


@dataclass(frozen=True)
class Scenario:
    id: str
    name: str
    description: str
    user_request: str
    untrusted_document: str | None = None


@dataclass(frozen=True)
class ToolOutput:
    message: str
    data: dict[str, str | int]


@dataclass(frozen=True)
class GuardedResult:
    status: ExecutionStatus
    event: SecurityEvent
    executed: bool
    output: ToolOutput | None = None


@dataclass(frozen=True)
class SimulationStep:
    step_number: int
    description: str
    input_trust: InputTrust
    input_content: str | None = None
    tool: str | None = None
    action: str | None = None
    resource: str | None = None
    record_count: int | None = None
    destination: str | None = None
    contains_sensitive_data: bool | None = None
    decision: Decision | None = None
    risk_score: int | None = None
    severity: Severity | None = None
    triggered_policies: tuple[PolicyMatch, ...] = ()
    explanation: str | None = None
    executed: bool = False
    event_id: UUID | None = None
    execution_status: ExecutionStatus | None = None
    output: ToolOutput | None = None


@dataclass(frozen=True)
class ScenarioResult:
    scenario_id: str
    scenario_name: str
    status: ScenarioStatus
    summary: str
    steps: tuple[SimulationStep, ...]
