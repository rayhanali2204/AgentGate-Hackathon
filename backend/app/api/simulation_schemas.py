"""HTTP response schemas for the deterministic scenario timeline."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict

from ..models import Decision, Severity
from ..simulation.models import ExecutionStatus, InputTrust, ScenarioStatus
from .schemas import PolicyMatchSchema


class ScenarioSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str


class ToolOutputSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message: str
    data: dict[str, str | int]


class SimulationStepSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    step_number: int
    description: str
    input_trust: InputTrust
    input_content: str | None
    tool: str | None
    action: str | None
    resource: str | None
    record_count: int | None
    destination: str | None
    contains_sensitive_data: bool | None
    decision: Decision | None
    risk_score: int | None
    severity: Severity | None
    triggered_policies: list[PolicyMatchSchema]
    explanation: str | None
    executed: bool
    event_id: UUID | None
    execution_status: ExecutionStatus | None
    output: ToolOutputSchema | None


class ScenarioResultSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    scenario_id: str
    scenario_name: str
    status: ScenarioStatus
    summary: str
    steps: list[SimulationStepSchema]
