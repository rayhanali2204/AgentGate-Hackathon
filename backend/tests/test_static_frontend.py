from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def frontend_dist(tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text('<!doctype html><html><title>AgentGate</title><div id="root"></div></html>')
    (dist / "assets").mkdir()
    (dist / "assets" / "app-test.js").write_text('console.log("AgentGate");')
    (dist / "assets" / "app-test.css").write_text('body { color: white; }')
    return dist


@pytest.fixture
def client(frontend_dist):
    with TestClient(create_app(frontend_dist=frontend_dist)) as client:
        yield client


def test_health_stays_json(client):
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "AgentGate"}
    assert response.headers['content-type'] == 'application/json'


@pytest.mark.parametrize('path', ['/', '/index.html', '/dashboard', '/dashboard/events'])
def test_frontend_root_and_spa_paths(client, path):
    response = client.get(path)
    assert response.status_code == 200
    assert '<title>AgentGate</title>' in response.text
    assert response.headers['content-type'].startswith('text/html')
    assert response.headers['cache-control'] == 'no-cache'


@pytest.mark.parametrize('path,content_type,content', [
    ('/assets/app-test.js', 'javascript', 'console.log'),
    ('/assets/app-test.css', 'text/css', 'color: white'),
])
def test_static_assets(client, path, content_type, content):
    response = client.get(path)
    assert response.status_code == 200
    assert content_type in response.headers['content-type']
    assert content in response.text


@pytest.mark.parametrize('method', ['GET', 'POST', 'PUT', 'DELETE'])
@pytest.mark.parametrize('path', ['/api', '/api/missing', '/api/missing/route', '/api/missing.js'])
def test_unknown_api_never_returns_spa(client, method, path):
    response = client.request(method, path)
    assert response.status_code == 404
    assert response.headers['content-type'] == 'application/json'
    assert response.json() == {'detail': 'Not Found'}


@pytest.mark.parametrize('path', ['/assets/missing.js', '/missing.css', '/assets/missing', '/.env', '/.git/config', '/%2e%2e/secret.txt'])
def test_missing_assets_and_private_paths_are_not_spa(client, path):
    assert client.get(path).status_code == 404


def test_head_root_and_non_get_ui(client):
    response = client.head('/')
    assert response.status_code == 200
    assert response.content == b''
    assert client.post('/dashboard').status_code == 405


def test_api_validation_and_404_preserved(client):
    assert client.post('/api/evaluate', json={}).status_code == 422
    assert client.get(f'/api/events/{uuid4()}').status_code == 404
    assert client.post('/api/scenarios/missing/run').status_code == 404
    assert client.get('/openapi.json').json()['info']['title'] == 'AgentGate API'
    assert client.get('/docs').status_code == 200


@pytest.mark.parametrize('scenario_id,status,executed', [
    ('normal-support', 'SUCCESS', True),
    ('prompt-injection', 'ATTACK_BLOCKED', False),
    ('destructive-approval', 'APPROVAL_REQUIRED', False),
])
def test_scenarios_work_with_frontend_mounted(client, scenario_id, status, executed):
    response = client.post(f'/api/scenarios/{scenario_id}/run')
    assert response.status_code == 200
    result = response.json()
    assert result['status'] == status
    actions = [step for step in result['steps'] if step['event_id']]
    assert all(step['executed'] is executed for step in actions)
    if scenario_id == 'prompt-injection':
        assert (actions[0]['decision'], actions[0]['risk_score'], actions[0]['severity']) == ('BLOCK', 80, 'CRITICAL')
    assert {step['event_id'] for step in actions} == {event['event_id'] for event in client.get('/api/events').json()}


def test_missing_dist_keeps_api_usable(tmp_path):
    with TestClient(create_app(frontend_dist=tmp_path / 'missing')) as client:
        assert client.get('/api/health').status_code == 200
        assert client.get('/').status_code == 404
        assert client.get('/api/missing').status_code == 404


def test_dist_without_index_does_not_mount(tmp_path):
    with TestClient(create_app(frontend_dist=tmp_path)) as client:
        assert client.get('/').status_code == 404
        assert client.get('/api/health').status_code == 200


def test_environment_path_and_explicit_override(frontend_dist, tmp_path, monkeypatch):
    monkeypatch.setenv('FRONTEND_DIST_PATH', str(frontend_dist))
    with TestClient(create_app()) as client:
        assert client.get('/').status_code == 200
    with TestClient(create_app(frontend_dist=tmp_path / 'absent')) as client:
        assert client.get('/').status_code == 404


def test_symlink_cannot_escape_static_root(frontend_dist, tmp_path):
    secret = tmp_path / 'secret.txt'
    secret.write_text('not public')
    (frontend_dist / 'leak.txt').symlink_to(secret)
    with TestClient(create_app(frontend_dist=frontend_dist)) as client:
        assert client.get('/leak.txt').status_code == 404
