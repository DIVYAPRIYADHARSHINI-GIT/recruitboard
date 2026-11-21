"""Atomic SQL quotas shared by all instances. Keys are hashed, not raw IPs."""
import hashlib
import json
import time
from sqlalchemy import case, delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from .models import RateBucket


class DatabaseLimiter:
    def __init__(self, engine, clock=time.time):
        self.engine = engine
        self.clock = clock

    def allow(self, key, limit, window=60):
        if limit < 1 or window < 1:
            return False
        timestamp = int(self.clock())
        start = timestamp // window * window
        hashed = hashlib.sha256(json.dumps([key, window], separators=(',', ':')).encode()).hexdigest()
        insert = sqlite_insert if self.engine.dialect.name == 'sqlite' else pg_insert
        statement = insert(RateBucket).values(key_digest=hashed, window_start=start, expires_at=start+window, hits=1)
        statement = statement.on_conflict_do_update(
            index_elements=['key_digest', 'window_start'],
            set_={'hits': case((RateBucket.hits < limit+1, RateBucket.hits+1), else_=RateBucket.hits)},
        ).returning(RateBucket.hits)
        with self.engine.begin() as connection:
            connection.execute(delete(RateBucket).where(RateBucket.expires_at <= timestamp))
            hits = connection.scalar(statement)
        return hits <= limit