from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.config import Config
from app.main import create_app
from app.models import Candidate, RateBucket
from app.rate_limit import DatabaseLimiter
from test_foundation import client, auth


def test_adapter_without_lifespan_still_initializes(tmp_path):
    app = create_app(Config(database_url=f'sqlite:///{tmp_path}/adapter.db', demo=True, seed=True, secure=False, origins=('http://testserver',)))
    # Intentionally NOT a context manager: no lifespan callback is triggered.
    with_lifespan_disabled = TestClient(app, headers={'Origin': 'http://testserver'})
    try:
        assert with_lifespan_disabled.get('/health').json() == {'status': 'ok'}
        auth(with_lifespan_disabled)
        assert with_lifespan_disabled.get('/api/candidates').json()['total'] == 40
    finally:
        with_lifespan_disabled.close()
        app.state.engine.dispose()


def test_initialization_only_once_per_process(client, monkeypatch):
    import app.main as main
    def unexpected(*args, **kwargs):
        raise AssertionError('An already initialized app must not migrate on every request')
    monkeypatch.setattr(main, 'initialize', unexpected)
    assert client.get('/health').status_code == 200
    assert client.get('/api/auth/session').status_code == 200


def test_two_instances_share_one_rate_quota(client):
    first = DatabaseLimiter(client.app.state.engine, clock=lambda: 1800000001)
    second = DatabaseLimiter(client.app.state.engine, clock=lambda: 1800000001)
    assert first.allow(('TEST', 'same-client'), 2)
    assert second.allow(('TEST', 'same-client'), 2)
    assert not first.allow(('TEST', 'same-client'), 2)
    assert not second.allow(('TEST', 'same-client'), 2)


def test_rate_window_expiry_and_key_privacy(client):
    clock = [1800000001]
    limiter = DatabaseLimiter(client.app.state.engine, clock=lambda: clock[0])
    assert limiter.allow(('TEST', 'test-client-not-stored'), 1)
    assert not limiter.allow(('TEST', 'test-client-not-stored'), 1)
    with Session(client.app.state.engine) as db:
        bucket = db.scalar(select(RateBucket))
        assert len(bucket.key_digest) == 64
        assert 'test-client' not in bucket.key_digest
    clock[0] += 60
    assert limiter.allow(('TEST', 'test-client-not-stored'), 1)
    with Session(client.app.state.engine) as db:
        assert db.scalar(select(func.count()).select_from(RateBucket)) == 1


def test_atomic_counter_handles_small_concurrent_unit_fixture(client):
    # Six unit-level counter operations against isolated SQLite, not a load test or network call.
    limiter = DatabaseLimiter(client.app.state.engine, clock=lambda: 1800000001)
    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(lambda _: limiter.allow(('TEST', 'atomic'), 3), range(6)))
    assert sum(results) == 3


def test_failed_initialization_does_not_expose_details(tmp_path, monkeypatch, caplog):
    import app.main as main
    app = create_app(Config(database_url=f'sqlite:///{tmp_path}/failure.db', secure=False))
    def failing(*args, **kwargs):
        raise RuntimeError('TEST_PRIVATE_DIAGNOSTIC_MUST_NOT_APPEAR')
    monkeypatch.setattr(main, 'initialize', failing)
    no_lifespan = TestClient(app)
    try:
        response = no_lifespan.get('/health')
        assert response.status_code == 503
        assert 'TEST_PRIVATE' not in response.text
        assert 'TEST_PRIVATE' not in caplog.text
        assert 'RuntimeError' in caplog.text
    finally:
        no_lifespan.close()
        app.state.engine.dispose()


def test_separate_cold_app_start_keeps_seed_idempotent(client):
    app = create_app(client.app.state.config)
    with TestClient(app) as another:
        assert another.get('/health').status_code == 200
    with Session(client.app.state.engine) as db:
        assert db.scalar(select(func.count()).select_from(Candidate)) == 40


def test_rate_limits_cannot_be_reset_by_new_limiter(client):
    first = DatabaseLimiter(client.app.state.engine, clock=lambda: 1800000001)
    assert first.allow(('TEST', 'restart'), 1)
    replacement = DatabaseLimiter(client.app.state.engine, clock=lambda: 1800000001)
    assert not replacement.allow(('TEST', 'restart'), 1)