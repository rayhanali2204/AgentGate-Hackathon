"""Thin routes: validate input, invoke the engine, and access the audit store."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request

from ..events import SecurityEventStore
from ..evaluation import evaluate_and_record
from ..models import Decision, Severity
from ..permissions import permissions_for
from .schemas import EvaluationResponse, HealthResponse, SecurityEventResponse, ToolRequestSchema

router = APIRouter(prefix="/api")

def get_event_store(request: Request) -> SecurityEventStore:
    return request.app.state.event_store


StoreDependency = Annotated[SecurityEventStore, Depends(get_event_store)]


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="AgentGate")


@router.post("/evaluate", response_model=EvaluationResponse)
def evaluate(payload: ToolRequestSchema, store: StoreDependency) -> EvaluationResponse:
    request = payload.to_domain()
    event = evaluate_and_record(request, permissions_for(request.agent_id), store)
    return EvaluationResponse.model_validate(event)


@router.get("/events", response_model=list[SecurityEventResponse])
def list_events(
    store: StoreDependency, agent_id: str | None = None,
    decision: Decision | None = None, severity: Severity | None = None,
) -> list[SecurityEventResponse]:
    return [SecurityEventResponse.model_validate(event) for event in store.list_events(
        agent_id=agent_id, decision=decision, severity=severity,
    )]


@router.get("/events/{event_id}", response_model=SecurityEventResponse)
def get_event(event_id: UUID, store: StoreDependency) -> SecurityEventResponse:
    event = store.get(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Security event not found")
    return SecurityEventResponse.model_validate(event)
