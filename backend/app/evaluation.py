"""Shared evaluate-and-audit operation, independent of HTTP and simulation."""

from .events import SecurityEvent, SecurityEventStore
from .gateway import evaluate_request
from .models import AgentPermissions, ToolRequest


def evaluate_and_record(
    request: ToolRequest, permissions: AgentPermissions, store: SecurityEventStore,
) -> SecurityEvent:
    event = SecurityEvent.from_evaluation(request, evaluate_request(request, permissions))
    store.add(event)
    return event
