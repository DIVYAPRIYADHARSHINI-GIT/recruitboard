from itertools import count
from sqlalchemy import event, func, select, update
from sqlalchemy.orm import Session
from app.db import initialize, make_engine
from app.models import Application, Candidate, Job, RejectionReason, User
from app.seed import seed_demo


def test_seed_uses_real_generated_ids_after_sequence_offsets(tmp_path):
    engine = make_engine(f'sqlite:///{tmp_path}/sequence.db')
    initialize(engine, seed=False)
    with Session(engine) as db:
        db.execute(update(RejectionReason).values(id=RejectionReason.id+1000))
        db.commit()
        users, jobs = count(100), count(200)
        def offset_ids(session, flush_context, instances):
            for obj in session.new:
                if isinstance(obj, User) and obj.id is None:
                    obj.id = next(users)
                elif isinstance(obj, Job) and obj.id is None:
                    obj.id = next(jobs)
        # Simulate a database whose sequences are not starting at 1 (e.g. after rollback).
        event.listen(db, 'before_flush', offset_ids)
        assert seed_demo(db) is True
        db.commit()
        assert db.scalar(select(func.count()).select_from(Candidate)) == 40
        assert db.scalar(select(func.min(Application.job_id))) >= 200
        assert seed_demo(db) is False
    engine.dispose()


def test_seed_refuses_nonempty_business_database_without_users(tmp_path):
    engine = make_engine(f'sqlite:///{tmp_path}/existing.db')
    initialize(engine, seed=False)
    with Session(engine) as db:
        db.add(Job(title='TEST Existing job', department='TEST', location='TEST', openings=1, status='open'))
        db.commit()
        assert seed_demo(db) is False
        assert db.scalar(select(func.count()).select_from(User)) == 0
        assert db.scalar(select(func.count()).select_from(Candidate)) == 0
    engine.dispose()
