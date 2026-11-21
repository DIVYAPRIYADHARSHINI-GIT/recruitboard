"""Shared fixed-window rate limits for serverless instances; no candidate data."""
from alembic import op
import sqlalchemy as sa

revision = '0002'
down_revision = '0001'


def upgrade():
    op.create_table(
        'rate_buckets',
        sa.Column('key_digest', sa.String(64), primary_key=True),
        sa.Column('window_start', sa.BigInteger, primary_key=True),
        sa.Column('expires_at', sa.BigInteger, nullable=False),
        sa.Column('hits', sa.Integer, nullable=False),
        sa.CheckConstraint('hits >= 1'),
    )
    op.create_index('ix_rate_buckets_expires_at', 'rate_buckets', ['expires_at'])


def downgrade():
    op.drop_table('rate_buckets')