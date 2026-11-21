import secrets
from datetime import timedelta
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from test_foundation import client, auth
from app.models import AuthSession, Base, Candidate, Interview, RejectionReason, User, now
from app.security import csrf_for, hasher


def test_secure_http_only_cookie_and_exact_cors(client):
    client.app.state.config.secure = True
    response = client.get('/api/auth/session')
    assert 'Secure' in response.headers['set-cookie']
    assert 'HttpOnly' in response.headers['set-cookie']
    assert 'Domain=' not in response.headers['set-cookie']
    assert 'no-store' in response.headers['cache-control']
    assert response.headers['access-control-allow-origin'] == 'http://testserver'
    blocked = client.get('/api/auth/session', headers={'Origin': 'https://hostile.invalid'})
    assert 'access-control-allow-origin' not in blocked.headers


def test_forged_cookie_with_matching_csrf_is_not_a_session(client):
    sid = secrets.token_urlsafe(32)
    client.cookies.set('rb_session', sid)
    response = client.post('/api/auth/demo', json={'role': 'admin'}, headers={'X-CSRF-Token': csrf_for(sid)})
    assert response.status_code == 403


def test_expired_session_denies_reads_and_writes(client):
    auth(client)
    with Session(client.app.state.engine) as db:
        db.execute(update(AuthSession).values(expires_at=now()-timedelta(minutes=1)))
        db.commit()
    assert client.get('/api/candidates').status_code == 401
    assert client.post('/api/jobs', json={}).status_code == 403


def test_user_role_change_revokes_real_password_session(client):
    auth(client, 'admin')
    password = secrets.token_urlsafe(24)
    response = client.post('/api/users', json={'name': 'TEST Revocation Account', 'email': 'test.revocation@example.invalid', 'password': password, 'role': 'interviewer'})
    uid = response.json()['id']
    with TestClient(client.app, headers={'Origin': 'http://testserver'}) as other:
        other.headers['X-CSRF-Token'] = other.get('/api/auth/session').json()['csrf']
        response = other.post('/api/auth/login', json={'email': 'test.revocation@example.invalid', 'password': password})
        assert response.status_code == 200
        other.headers['X-CSRF-Token'] = response.json()['csrf']
        assert other.get('/api/candidates').status_code == 200
        assert client.patch(f'/api/users/{uid}', json={'role': 'recruiter', 'active': True}).status_code == 200
        assert other.get('/api/candidates').status_code == 401


def test_deactivation_checked_on_each_request(client):
    user = auth(client, 'interviewer')
    with Session(client.app.state.engine) as db:
        db.execute(update(User).where(User.id == user['id']).values(active=False))
        db.commit()
    assert client.get('/api/interviews').status_code == 401


def test_migration_schema_matches_models(client):
    with client.app.state.engine.connect() as connection:
        differences = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    assert differences == []


def test_job_list_and_search_counts_cannot_leak_unassigned_data(client):
    user = auth(client, 'interviewer')
    with Session(client.app.state.engine) as db:
        db.execute(delete(Interview).where(Interview.interviewer_id == user['id']))
        db.commit()
    assert client.get('/api/jobs').json() == []
    for suffix in ['', '?q=fictional', '?source=referral', '?job=1&stage=applied', '?tag=portfolio', '?sort=name&page=2']:
        result = client.get('/api/candidates'+suffix).json()
        assert result['total'] == 0 and result['items'] == []
    assert client.get('/api/interviews').json()['total'] == 0
    assert client.get('/api/notifications').json() == []


def test_unknown_sensitive_fields_rejected_without_echo(client):
    auth(client)
    response = client.post('/api/candidates', json={'name': 'TEST Input', 'email': 'test.extra@example.invalid', 'job_id': 1, 'anonymized': True})
    assert response.status_code == 422 and 'test.extra' not in response.text


def test_inactive_rejection_reason_blocked(client):
    auth(client)
    with Session(client.app.state.engine) as db:
        db.execute(update(RejectionReason).where(RejectionReason.id == 1).values(active=False))
        db.commit()
    assert client.post('/api/applications/1/stage', json={'stage': 'rejected', 'version': 1, 'reason_id': 1}).status_code == 422


def test_invalid_content_length_is_handled(client):
    assert client.get('/api/auth/session', headers={'Content-Length': 'not-a-number'}).status_code == 413
