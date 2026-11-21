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
    engine = create_engine(url, pool_pre_ping=True, hide_parameters=True, **({'connect_args': {'check_same_thread': False, 'timeout': 30}} if url.startswith('sqlite') else {'pool_size': 3, 'max_overflow': 2}))
    if engine.dialect.name == 'sqlite':
        @event.listens_for(engine, 'connect')
        def foreign_keys(connection, _):
            connection.execute('PRAGMA foreign_keys=ON')
    return engine


@contextmanager
def migration_lock(engine):
    if engine.dialect.name == 'postgresql':
        with engine.connect() as connection:
            connection.execute(text('SELECT pg_advisory_lock(78436219)'))
            connection.commit()
            try:
                yield connection
            finally:
                connection.execute(text('SELECT pg_advisory_unlock(78436219)'))
                connection.commit()
    else:
        import fcntl
        lock = Path(str(engine.url.database) + '.lock-db')
        with lock.open('a') as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            try:
                with engine.connect() as connection:
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
        with Session(connection) as db:
            defaults(db)
            if seed:
                seed_demo(db)
            db.commit()
        connection.commit()


def get_db(request):
    with Session(request.app.state.engine) as db:
        yield db