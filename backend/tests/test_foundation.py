import secrets
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session
from app.config import Config
from app.db import initialize
from app.main import create_app
from app.models import Candidate, User, StageHistory
from app.security import hasher


@pytest.fixture
def client(tmp_path):
    app = create_app(Config(database_url=f'sqlite:///{tmp_path}/test.db', demo=True, seed=True, secure=False, origins=('http://testserver',)))
    with TestClient(app, headers={'Origin': 'http://testserver'}) as c:
        yield c


def auth(client, role='recruiter'):
    token = client.get('/api/auth/session').json()['csrf']
    client.headers['X-CSRF-Token'] = token
    response = client.post('/api/auth/demo', json={'role': role})
    assert response.status_code == 200
    client.headers['X-CSRF-Token'] = response.json()['csrf']
    return response.json()['user']


def test_health_queries_database(client):
    assert client.get('/health').json() == {'status': 'ok'}


def test_seed_and_migrations_idempotent(client):
    initialize(client.app.state.engine, True)
    with Session(client.app.state.engine) as db:
        assert db.scalar(select(func.count()).select_from(Candidate)) == 40
        assert db.scalar(select(func.count()).select_from(User)) == 6
        assert db.scalar(select(func.count()).select_from(StageHistory)) > 40
        assert db.scalar(text('SELECT version_num FROM alembic_version')) == '0002'


@pytest.mark.parametrize('role', ['admin', 'recruiter', 'interviewer'])
def test_demo_roles_session_rotation(client, role):
    before = client.get('/api/auth/session')
    cookie_before = client.cookies.get('rb_session')
    assert 'HttpOnly' in before.headers['set-cookie']
    assert 'SameSite=lax' in before.headers['set-cookie']
    user = auth(client, role)
    assert user['role'] == role
    assert client.cookies.get('rb_session') != cookie_before
    assert 'password_hash' not in user
    assert client.post('/api/auth/logout').status_code == 200
    assert client.get('/api/auth/session').json()['user'] is None


def test_csrf_and_origin_required(client):
    assert client.post('/api/auth/demo', json={'role': 'admin'}).status_code == 403
    auth(client)
    assert client.post('/api/auth/demo', json={'role': 'admin'}, headers={'Origin': 'https://hostile.invalid'}).status_code == 403
    assert client.post('/api/auth/demo', json={'role': 'admin'}, headers={'X-CSRF-Token': 'wrong'}).status_code == 403


def test_demo_off(client):
    auth(client)
    client.app.state.config.demo = False
    assert client.post('/api/auth/demo', json={'role': 'admin'}).status_code == 404


def test_argon2id_real_login_and_generic_validation(client):
    password = secrets.token_urlsafe(24)
    with Session(client.app.state.engine) as db:
        encoded = hasher.hash(password)
        assert encoded.startswith('$argon2id$')
        db.add(User(name='TEST Local User', email='test.local@example.invalid', password_hash=encoded, role='recruiter', active=True, demo=False))
        db.commit()
    auth(client)
    response = client.post('/api/auth/login', json={'email': 'test.local@example.invalid', 'password': password})
    assert response.status_code == 200
    client.headers['X-CSRF-Token'] = response.json()['csrf']
    rejected = client.post('/api/auth/login', json={'email': 'not-valid', 'password': password})
    assert rejected.status_code == 422 and password not in rejected.text


def test_login_rate_limit(client):
    auth(client)
    client.app.state.config.login_limit = 2
    assert client.post('/api/auth/demo', json={'role': 'admin'}).status_code == 200
    assert client.post('/api/auth/demo', json={'role': 'admin'}).status_code == 429


def test_production_safety_guards():
    with pytest.raises(RuntimeError):
        create_app(Config(environment='production', secure=False))