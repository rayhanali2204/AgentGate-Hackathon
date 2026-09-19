from dataclasses import replace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.events import InMemorySecurityEventStore
from app.main import create_app
from app.models import Decision, Severity, ToolRequest
from app.permissions import DEMO_PERMISSIONS
from app.simulation.agent import SimulatedAgent
from app.simulation.executor import GuardedExecutor
from app.simulation.models import ExecutionStatus, InputTrust, ScenarioStatus
from app.simulation.scenarios import SCENARIOS, get_scenario
from app.simulation.tools import SimulatedTools


@pytest.fixture
def store():
    return InMemorySecurityEventStore()


@pytest.fixture
def tools():
    return SimulatedTools()


@pytest.fixture
def executor(store, tools):
    return GuardedExecutor(DEMO_PERMISSIONS, store, tools)


@pytest.fixture
def client(store):
    with TestClient(create_app(store)) as client:
        yield client


def run(executor, scenario_id):
    scenario = get_scenario(scenario_id)
    assert scenario is not None
    return SimulatedAgent(executor).run(scenario)


@pytest.mark.parametrize('scenario_id', ['normal-support', 'prompt-injection', 'destructive-approval'])
def test_scenario_exists(scenario_id):
    scenario = get_scenario(scenario_id)
    assert scenario.id == scenario_id
    assert scenario.name and scenario.description and scenario.user_request


def test_normal_executes_tracking_and_email(executor, tools, store):
    result = run(executor, 'normal-support')
    assert result.status == ScenarioStatus.SUCCESS
    lookup, email = result.steps[1:]
    assert [(s.tool, s.action, s.decision, s.executed) for s in (lookup, email)] == [
        ('orders', 'lookup', Decision.ALLOW, True), ('email', 'send', Decision.ALLOW, True),
    ]
    assert len(tools.executed_requests) == 2
    assert lookup.output.data['tracking_number'] in email.output.data['body']
    assert email.output.data['recipient'] == lookup.output.data['customer_email']
    assert email.output.data['status'] == 'simulated'
    assert len(store.list_events()) == 2
    assert [s.step_number for s in result.steps] == [1, 2, 3]
    assert all(s.risk_score == 0 for s in (lookup, email))


def test_attack_boundary(executor, tools, store):
    # Spy on the real adapter, rather than trusting the returned executed flag.
    tools.execute = Mock(wraps=tools.execute)
    result = run(executor, 'prompt-injection')
    assert result.status == ScenarioStatus.ATTACK_BLOCKED
    trusted, untrusted, attack = result.steps
    assert trusted.input_trust == InputTrust.TRUSTED
    assert 'order #4821' in trusted.input_content
    assert untrusted.input_trust == InputTrust.UNTRUSTED
    assert 'Ignore previous instructions' in untrusted.input_content
    assert attack.input_trust == InputTrust.UNTRUSTED
    assert (attack.tool, attack.action, attack.resource) == ('customer_database', 'read', 'customers')
    assert (attack.record_count, attack.destination, attack.contains_sensitive_data) == (5000, 'external', True)
    assert (attack.decision, attack.risk_score, attack.severity) == (Decision.BLOCK, 80, Severity.CRITICAL)
    assert {p.policy_id for p in attack.triggered_policies} == {'bulk_sensitive_data_export', 'external_sensitive_data_transfer'}
    assert not attack.executed
    assert attack.output is None
    assert attack.execution_status == ExecutionStatus.BLOCKED
    tools.execute.assert_not_called()
    assert tools.executed_requests == ()
    event = store.get(attack.event_id)
    assert event.decision == Decision.BLOCK
    assert event.risk_score == 80
    assert len(store.list_events()) == 1
    assert 'manipulated' in result.summary


def test_approval_never_executes(executor, tools, store):
    tools.execute = Mock(wraps=tools.execute)
    result = run(executor, 'destructive-approval')
    assert result.status == ScenarioStatus.APPROVAL_REQUIRED
    step = result.steps[-1]
    assert step.action == 'delete'
    assert step.decision == Decision.REQUIRE_APPROVAL
    assert step.execution_status == ExecutionStatus.PENDING_APPROVAL
    assert step.risk_score == 25
    assert not step.executed and step.output is None
    tools.execute.assert_not_called()
    assert len(store.list_events()) == 1


def test_database_adapter_only_executes_when_allowed(executor, tools):
    result = executor.execute(ToolRequest('customer-support-agent', 'customer_database', 'read', 'customers'))
    assert result.executed and result.event.decision == Decision.ALLOW
    assert result.output.data['email'] == 'demo@example.invalid'
    assert len(tools.executed_requests) == 1


def test_event_exists_before_tool_execution(store):
    tools = SimulatedTools()
    original = tools.execute

    def checked_execute(request):
        assert len(store.list_events()) == 1
        assert store.list_events()[0].decision == Decision.ALLOW
        return original(request)

    tools.execute = Mock(side_effect=checked_execute)
    executor = GuardedExecutor(DEMO_PERMISSIONS, store, tools)
    executor.execute(ToolRequest('customer-support-agent', 'orders', 'lookup', 'orders/4821'))
    tools.execute.assert_called_once()


def test_audit_failure_prevents_tool_execution(tools):
    store = Mock(spec=InMemorySecurityEventStore)
    store.add.side_effect = RuntimeError('audit unavailable')
    tools.execute = Mock(wraps=tools.execute)
    executor = GuardedExecutor(DEMO_PERMISSIONS, store, tools)
    with pytest.raises(RuntimeError, match='audit unavailable'):
        executor.execute(ToolRequest('customer-support-agent', 'orders', 'lookup', 'orders/4821'))
    tools.execute.assert_not_called()


def test_disallowed_normal_lookup_stops_email(store, tools):
    permissions = replace(DEMO_PERMISSIONS, allowed_tools={'email'})
    result = run(GuardedExecutor(permissions, store, tools), 'normal-support')
    assert result.status == ScenarioStatus.STOPPED
    assert len(result.steps) == 2
    assert tools.executed_requests == ()
    assert len(store.list_events()) == 1


@pytest.mark.parametrize('changes', [{'agent_id': 'impostor'}, {'tool': 'shell'}, {'action': 'unknown'}])
def test_guard_uses_engine_for_all_proposals(executor, tools, changes):
    request = replace(ToolRequest('customer-support-agent', 'orders', 'lookup', 'orders/4821'), **changes)
    assert executor.execute(request).event.decision == Decision.BLOCK
    assert tools.executed_requests == ()


def test_scenario_listing(client):
    response = client.get('/api/scenarios')
    assert response.status_code == 200
    assert response.json() == [{'id': s.id, 'name': s.name, 'description': s.description} for s in SCENARIOS]
    assert client.get('/api/events').json() == []


@pytest.mark.parametrize('scenario_id,status,event_count', [
    ('normal-support', 'SUCCESS', 2),
    ('prompt-injection', 'ATTACK_BLOCKED', 1),
    ('destructive-approval', 'APPROVAL_REQUIRED', 1),
])
def test_scenario_api_and_existing_audit_endpoints(client, scenario_id, status, event_count):
    response = client.post(f'/api/scenarios/{scenario_id}/run')
    assert response.status_code == 200
    result = response.json()
    assert result['scenario_id'] == scenario_id
    assert result['status'] == status
    assert result['scenario_name'] and result['summary']
    steps = result['steps']
    assert [s['step_number'] for s in steps] == list(range(1, len(steps) + 1))
    action_steps = [s for s in steps if s['event_id']]
    assert len(action_steps) == event_count
    events = client.get('/api/events').json()
    assert len(events) == event_count
    for step in action_steps:
        event = client.get('/api/events/' + step['event_id']).json()
        for field in ('decision', 'risk_score', 'severity', 'tool', 'action', 'resource', 'triggered_policies', 'explanation'):
            assert event[field] == step[field]
        assert step['executed'] == (step['decision'] == 'ALLOW')
    if scenario_id == 'prompt-injection':
        attack = action_steps[0]
        assert (attack['decision'], attack['risk_score'], attack['severity'], attack['executed']) == ('BLOCK', 80, 'CRITICAL', False)
        assert client.get('/api/events?decision=BLOCK&severity=CRITICAL').json() == events


def test_unknown_scenario_404_without_event(client):
    response = client.post('/api/scenarios/unknown/run')
    assert response.status_code == 404
    assert response.json() == {'detail': 'Scenario not found'}
    assert client.get('/api/events').json() == []


def test_scenario_and_evaluate_share_store(client):
    client.post('/api/scenarios/prompt-injection/run')
    client.post('/api/evaluate', json={'agent_id': 'customer-support-agent', 'tool': 'orders', 'action': 'lookup', 'resource': 'orders/4821'})
    assert len(client.get('/api/events').json()) == 2


def test_repeated_runs_have_independent_tool_state_and_unique_events(client):
    first = client.post('/api/scenarios/normal-support/run').json()
    second = client.post('/api/scenarios/normal-support/run').json()
    for result in (first, second):
        assert result['status'] == 'SUCCESS'
        assert sum(s['executed'] for s in result['steps']) == 2
    assert len({e['event_id'] for e in client.get('/api/events').json()}) == 4
    for left, right in zip(first['steps'], second['steps']):
        assert {k: v for k, v in left.items() if k != 'event_id'} == {k: v for k, v in right.items() if k != 'event_id'}


def test_simulation_schema_is_in_openapi(client):
    paths = client.get('/openapi.json').json()['paths']
    assert '/api/scenarios' in paths
    assert '/api/scenarios/{scenario_id}/run' in paths
