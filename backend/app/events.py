"""Framework-independent audit events and replaceable event storage."""

from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Lock
from typing import Protocol
from uuid import UUID, uuid4

from .models import Decision, PolicyMatch, SecurityDecision, Severity, ToolRequest


@dataclass(frozen=True)
class SecurityEvent:
    event_id: UUID
    timestamp: datetime
    agent_id: str
    tool: str
    action: str
    resource: str
    record_count: int
    destination: str | None
    contains_sensitive_data: bool
    decision: Decision
    risk_score: int
    severity: Severity
    triggered_policies: tuple[PolicyMatch, ...]
    explanation: str

    @classmethod
    def from_evaluation(cls, request: ToolRequest, result: SecurityDecision) -> "SecurityEvent":
        return cls(
            event_id=uuid4(), timestamp=datetime.now(UTC),
            agent_id=request.agent_id, tool=request.tool, action=request.action,
            resource=request.resource, record_count=request.record_count,
            destination=request.destination, contains_sensitive_data=request.contains_sensitive_data,
            decision=result.decision, risk_score=result.risk_score, severity=result.severity,
            triggered_policies=result.triggered_policies, explanation=result.explanation,
        )


class SecurityEventStore(Protocol):
    """Storage contract: append events, retrieve by ID, and list newest-first."""

    def add(self, event: SecurityEvent) -> None: ...

    def get(self, event_id: UUID) -> SecurityEvent | None: ...

    def list_events(
        self, *, agent_id: str | None = None, decision: Decision | None = None,
        severity: Severity | None = None,
    ) -> list[SecurityEvent]: ...


class InMemorySecurityEventStore:
    """Thread-safe, process-local store. New instances start empty."""

    def __init__(self) -> None:
        self._events: dict[UUID, SecurityEvent] = {}
        self._lock = Lock()

    def add(self, event: SecurityEvent) -> None:
        with self._lock:
            if event.event_id in self._events:
                raise ValueError("An event with this ID already exists")
            self._events[event.event_id] = event

    def get(self, event_id: UUID) -> SecurityEvent | None:
        with self._lock:
            return self._events.get(event_id)

    def list_events(
        self, *, agent_id: str | None = None, decision: Decision | None = None,
        severity: Severity | None = None,
    ) -> list[SecurityEvent]:
        with self._lock:
            # Reverse insertion order breaks equal-timestamp ties newest-first.
            events = list(reversed(self._events.values()))
        return sorted(
            (event for event in events
             if (agent_id is None or event.agent_id == agent_id)
             and (decision is None or event.decision == decision)
             and (severity is None or event.severity == severity)),
            key=lambda event: event.timestamp, reverse=True,
        )
