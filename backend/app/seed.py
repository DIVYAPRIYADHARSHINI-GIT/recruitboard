"""Fictional demo only. Safe to run repeatedly; never prints credentials."""
import secrets
from datetime import timedelta
from argon2 import PasswordHasher
from sqlalchemy import select
from .models import *

STAGES = ['applied', 'screening', 'interview', 'offer', 'hired', 'rejected']


def defaults(db):
    if not db.scalar(select(Stage.key).limit(1)):
        db.add_all([Stage(key=k, label=k.title(), position=i) for i, k in enumerate(STAGES)])
        db.add_all([Criterion(key=k, label=label, guidance='Use specific, job-relevant evidence. 1 = needs development; 5 = exceptional.') for k, label in [('technical', 'Technical skills'), ('communication', 'Communication'), ('culture', 'Culture fit')]])
        db.add_all([RejectionReason(label=x, active=True) for x in ['Skills alignment', 'Role expectations', 'Candidate withdrew', 'Position filled']])
        db.flush()


def seed_demo(db):
    defaults(db)
    if any(db.scalar(select(model.id).limit(1)) for model in (User, Job, Candidate, Application)):
        return False
    password_hash = PasswordHasher().hash(secrets.token_urlsafe(48))
    users = [('Demo Admin', 'admin', 'admin'), ('Demo Recruiter', 'recruiter', 'recruiter'), ('Demo Recruiter Two', 'recruiter.two', 'recruiter'), ('Demo Interviewer', 'interviewer', 'interviewer'), ('Demo Interviewer Two', 'interviewer.two', 'interviewer'), ('Demo Interviewer Three', 'interviewer.three', 'interviewer')]
    user_rows = [User(name=n, email=f'{e}@recruitboard.example', password_hash=password_hash, role=r, active=True, demo=True) for n, e, r in users]
    db.add_all(user_rows)
    db.flush()
    recruiter_id = user_rows[1].id
    interviewer_ids = [user.id for user in user_rows if user.role == 'interviewer']
    reason_ids = list(db.scalars(select(RejectionReason.id).where(RejectionReason.active.is_(True)).order_by(RejectionReason.id)))
    if not reason_ids:
        raise RuntimeError('Demo seed requires at least one active rejection reason.')
    jobs = [('Senior Product Designer', 'Design', 'Bengaluru · Hybrid', 2), ('Frontend Engineer', 'Engineering', 'Remote · India', 3), ('Customer Success Lead', 'Customer experience', 'Chennai · Hybrid', 1), ('Data Analyst', 'Analytics', 'Pune · Hybrid', 2), ('People Operations Partner', 'People', 'Remote · India', 1)]
    job_rows = [Job(title=title, department=dept, location=location, openings=openings, status='on_hold' if i == 4 else 'open') for i, (title, dept, location, openings) in enumerate(jobs)]
    db.add_all(job_rows)
    db.flush()
    first = ['Ari', 'Mira', 'Nila', 'Kian', 'Tara', 'Ravi', 'Lena', 'Ilan', 'Zoya', 'Neel']
    last = ['Vale', 'Reed', 'Solis', 'Wren']
    today = now()
    for i in range(40):
        created = today - timedelta(days=15 + (i * 7) % 74)
        target = STAGES[i % 6]
        candidate = Candidate(name=f'{first[i % 10]} {last[i // 10]}', email=f'fictional.candidate.{i+1}@example.invalid', phone='', source=['referral', 'job_portal', 'campus', 'website'][i % 4], notes='Fictional demo profile. Interested in collaborative teams and thoughtful products.', created_at=created)
        db.add(candidate)
        db.flush()
        db.add(CandidateTag(candidate_id=candidate.id, tag=['portfolio', 'remote', 'experienced', 'early-career'][i % 4]))
        application = Application(candidate_id=candidate.id, job_id=job_rows[i % len(job_rows)].id, stage=target, created_at=created, version=1)
        db.add(application)
        db.flush()
        path = STAGES[:STAGES.index(target)+1] if target != 'rejected' else ['applied', 'screening', 'rejected']
        for step, stage in enumerate(path):
            at = created + timedelta(days=step * 3)
            db.add(StageHistory(application_id=application.id, from_stage=path[step-1] if step else None, to_stage=stage, actor_id=recruiter_id, occurred_at=at, reason_id=reason_ids[i % len(reason_ids)] if stage == 'rejected' else None))
            db.add(Activity(candidate_id=candidate.id, actor_id=recruiter_id, kind='stage', summary=f'Application entered {stage.title()}', created_at=at))
        if target in ['interview', 'offer', 'hired']:
            interviewer = interviewer_ids[(i // 6) % len(interviewer_ids)]
            interview = Interview(application_id=application.id, interviewer_id=interviewer, starts_at=(today + timedelta(days=i % 7, hours=2)) if target == 'interview' else created + timedelta(days=7), mode=['video', 'phone', 'in_person'][i % 3], created_by=recruiter_id)
            db.add(interview)
            db.flush()
            db.add(Notification(recipient_id=interviewer, application_id=application.id, kind='assignment', message='An interview has been assigned to you.'))
            if target != 'interview':
                db.add(Scorecard(interview_id=interview.id, submitted_by=interviewer, technical=3+i%3, communication=4, culture=4, recommendation='yes', feedback='Fictional assessment: clear examples and considered trade-offs.', submitted_at=created+timedelta(days=8)))
                db.add(Notification(recipient_id=recruiter_id, application_id=application.id, kind='scorecard', message='A new scorecard is ready to review.'))
        if target in ['offer', 'hired']:
            db.add(Offer(application_id=application.id, status='accepted' if target == 'hired' else ('sent' if i % 2 else 'draft'), amount_minor=(1200000+i*10000)*100, updated_at=created+timedelta(days=10)))
        if target == 'rejected' and i % 2:
            db.add(Offer(application_id=application.id, status='declined', amount_minor=None, updated_at=created+timedelta(days=6)))
    db.flush()
    return True


if __name__ == '__main__':
    from .config import Config
    from .db import make_engine, initialize
    config = Config()
    config.validate()
    if not config.seed:
        raise SystemExit('Set SEED_DEMO=true explicitly to seed fictional data.')
    initialize(make_engine(config.database_url), seed=True)
    print('Demo initialization complete; existing users were not changed.')