from alembic import context
from app.models import Base

config = context.config
connection = config.attributes.get('connection')
if connection is None:
    from app.config import Config
    from app.db import make_engine
    engine = make_engine(Config().database_url)
    connection = engine.connect()

context.configure(connection=connection, target_metadata=Base.metadata, compare_type=True)
with context.begin_transaction():
    context.run_migrations()