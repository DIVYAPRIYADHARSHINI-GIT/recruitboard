"""No production connection. Verify locking contract and real local transactions."""
from contextlib import contextmanager
from types import SimpleNamespace
import pytest
from sqlalchemy import event, select, func, text
from sqlalchemy.orm import Session
import app.db as database
import app.seed as seed
from app.config import Config
from app.models import Candidate, User


class TransactionEngine:
    dialect = SimpleNamespace(name='postgresql')

    def __init__(self):
        self.statements = []
        self.active = False
        self.commits = 0
        self.rollbacks = 0

    @contextmanager
    def begin(self):
        assert not self.active
        self.active = True
        try:
            yield self
        except Exception:
            self.rollbacks += 1
            raise
        else:
            self.commits += 1
        finally:
            self.active = False

    def execute(self, statement):
        assert self.active
        self.statements.append(str(statement))


def test_pooler_config_is_accepted_without_relaxing_production_rules():
    # Non-credentialed .invalid host; no engine/network connection is made.
    config = Config(database_url='postgresql://test-pooler.example.invalid/demo', environment='production', origins=('https://recruitboard-pi.vercel.app',), secure=True)
    config.validate()
    config.secure = False
    with pytest.raises(RuntimeError, match='Secure cookies'):
        config.validate()
    config.secure = True
    config.origins = ('http://localhost:4173',)
    with pytest.raises(RuntimeError, match='HTTPS'):
        config.validate()


def test_transaction_lock_covers_entire_initialization_without_intermediate_commit():
    engine = TransactionEngine()
    with database.migration_lock(engine) as connection:
        assert connection is engine and engine.active
        assert engine.commits == 0
        connection.execute(text('SELECT 1'))
    assert engine.commits == 1 and not engine.active
    assert engine.statements == [
        "SET LOCAL statement_timeout = '15s'",
        "SET LOCAL lock_timeout = '10s'",
        'SELECT pg_advisory_xact_lock(78436219)',
        'SELECT 1',
    ]
    assert not any('pg_advisory_unlock' in s or 'pg_advisory_lock(' in s for s in engine.statements)


def test_failure_rolls_back_outer_transaction_releasing_lock():
    engine = TransactionEngine()
    with pytest.raises(RuntimeError, match='TEST rollback'):
        with database.migration_lock(engine):
            raise RuntimeError('TEST rollback')
    assert engine.rollbacks == 1 and engine.commits == 0 and not engine.active


def test_psycopg_connect_arguments_do_not_use_pooler_unsupported_startup_options(monkeypatch):
    captured = {}
    def fake_create(url, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(dialect=SimpleNamespace(name='postgresql'))
    monkeypatch.setattr(database, 'create_engine', fake_create)
    database.make_engine('postgresql://test-pooler.example.invalid/demo')
    assert captured['connect_args'] == {'connect_timeout': 10, 'prepare_threshold': None}
    assert captured['hide_parameters'] is True
    assert 'options' not in captured['connect_args']


def test_real_migration_and_seed_share_one_outer_transaction(tmp_path, monkeypatch):
    engine = database.make_engine(f'sqlite:///{tmp_path}/one-transaction.db')
    commits = []
    event.listen(engine, 'commit', lambda connection: commits.append(id(connection)))
    original_upgrade = database.command.upgrade
    original_seed = seed.seed_demo
    shared = []
    def upgrade(config, revision):
        connection = config.attributes['connection']
        assert connection.in_transaction()
        shared.append(connection)
        return original_upgrade(config, revision)
    def seed_inside(session):
        connection = session.connection()
        assert connection is shared[0] and connection.in_transaction()
        assert commits == []
        return original_seed(session)
    monkeypatch.setattr(database.command, 'upgrade', upgrade)
    monkeypatch.setattr(seed, 'seed_demo', seed_inside)
    database.initialize(engine, seed=True)
    assert len(commits) == 1
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(Candidate)) == 40
    engine.dispose()


def test_partial_seed_failure_leaves_no_committed_users_then_retry_succeeds(tmp_path, monkeypatch):
    engine = database.make_engine(f'sqlite:///{tmp_path}/seed-rollback.db')
    # Pre-create schema to test data rollback independently of SQLite DDL semantics.
    database.initialize(engine, seed=False)
    original = seed.seed_demo
    def fail_after_seed(session):
        original(session)
        session.flush()
        raise RuntimeError('TEST seed failure')
    with monkeypatch.context() as patch:
        patch.setattr(seed, 'seed_demo', fail_after_seed)
        with pytest.raises(RuntimeError, match='TEST seed failure'):
            database.initialize(engine, seed=True)
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(User)) == 0
        assert session.scalar(select(func.count()).select_from(Candidate)) == 0
    database.initialize(engine, seed=True)
    database.initialize(engine, seed=True)
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(User)) == 6
        assert session.scalar(select(func.count()).select_from(Candidate)) == 40
    engine.dispose()
