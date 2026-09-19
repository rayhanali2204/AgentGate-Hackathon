"""Pydantic models used only at the HTTP boundary."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr, field_validator

from ..models import Decision, Severity, ToolRequest


class ToolRequestSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_id: StrictStr
    tool: StrictStr
    action: StrictStr
    resource: StrictStr
    record_count: Annotated[StrictInt, Field(ge=1)] = 1
    destination: StrictStr | None = None
    contains_sensitive_data: StrictBool = False
    reason: StrictStr | None = None

    @field_validator("agent_id", "tool", "action", "resource")
    @classmethod
    def nonempty_string(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must be a non-empty string")
        return value

    def to_domain(self) -> ToolRequest:
        return ToolRequest(**self.model_dump())


class PolicyMatchSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    policy_id: str
    decision: Decision
    explanation: str


class EvaluationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: UUID
    decision: Decision
    risk_score: int
    severity: Severity
    triggered_policies: list[PolicyMatchSchema]
    explanation: str


class SecurityEventResponse(EvaluationResponse):
    timestamp: datetime
    agent_id: str
    tool: str
    action: str
    resource: str
    record_count: int
    destination: str | None
    contains_sensitive_data: bool


class HealthResponse(BaseModel):
    status: str
    service: str
