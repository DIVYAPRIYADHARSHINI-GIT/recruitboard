from contextlib import contextmanager
from pathlib import Path
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session
from alembic import command
from alembic.config import Config as AlembicConfig

ROOT = Path(__file__).resolve().parents[1]


def make_engine(url):
    if url.startswith('postgresql://'):
        url = url.replace('postgresql://', 'postgresql+psycopg://', 1)
    engine = create_engine(url, pool_pre_ping=True, hide_parameters=True, **({'connect_args': {'check_same_thread': False, 'timeout': 30}} if url.startswith('sqlite') else {'pool_size': 1, 'max_overflow': 1, 'pool_timeout': 10, 'connect_args': {'connect_timeout': 10, 'prepare_threshold': None}}))
    if engine.dialect.name == 'sqlite':
        @event.listens_for(engine, 'connect')
        def foreign_keys(connection, _):
            connection.execute('PRAGMA foreign_keys=ON')
    return engine


@contextmanager
def migration_lock(engine):
    if engine.dialect.name == 'postgresql':
        # The lock, migrations, and seed share ONE transaction/backend connection.
        # Safe for direct connections AND PgBouncer transaction-mode pooling.
        # Never commit inside this block or use session-level advisory locks here.
        with engine.begin() as connection:
            connection.execute(text("SET LOCAL statement_timeout = '15s'"))
            connection.execute(text("SET LOCAL lock_timeout = '10s'"))
            connection.execute(text('SELECT pg_advisory_xact_lock(78436219)'))
            yield connection
    else:
        import fcntl
        lock = Path(str(engine.url.database) + '.lock-db')
        with lock.open('a') as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            try:
                with engine.begin() as connection:
                    yield connection
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)


def initialize(engine, seed=False):
    with migration_lock(engine) as connection:
        config = AlembicConfig(str(ROOT / 'alembic.ini'))
        config.set_main_option('script_location', str(ROOT / 'migrations'))
        config.attributes['connection'] = connection
        command.upgrade(config, 'head')
        from .seed import defaults, seed_demo
        # Session.commit flushes but cannot commit the externally owned transaction.
        with Session(connection, join_transaction_mode='rollback_only') as db:
            defaults(db)
            if seed:
                seed_demo(db)
            db.commit()


def get_db(request):
    with Session(request.app.state.engine) as db:
        yield db