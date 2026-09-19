from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta

import pytest

from app.events import InMemorySecurityEventStore, SecurityEvent
from app.gateway import evaluate_request
from app.models import AgentPermissions, ToolRequest


def make_event():
    request = ToolRequest("agent", "tool", "read", "resource")
    return SecurityEvent.from_evaluation(request, evaluate_request(request, AgentPermissions("agent", {"tool"}, {"read"})))


def test_timestamp_order_and_ties():
    store = InMemorySecurityEventStore()
    first = make_event()
    older = replace(make_event(), timestamp=first.timestamp - timedelta(seconds=1))
    tied = replace(make_event(), timestamp=first.timestamp)
    for event in (first, older, tied):
        store.add(event)
    assert store.list_events() == [tied, first, older]


def test_duplicate_cannot_overwrite_audit_event():
    store = InMemorySecurityEventStore()
    event = make_event()
    store.add(event)
    with pytest.raises(ValueError):
        store.add(replace(event, explanation="altered"))
    assert store.get(event.event_id) == event


def test_returned_list_cannot_mutate_store():
    store = InMemorySecurityEventStore()
    store.add(make_event())
    store.list_events().clear()
    assert len(store.list_events()) == 1


def test_concurrent_event_writes():
    store = InMemorySecurityEventStore()
    events = [make_event() for _ in range(100)]
    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(store.add, events))
    assert {e.event_id for e in store.list_events()} == {e.event_id for e in events}
