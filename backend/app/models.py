from datetime import datetime, timezone
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    demo: Mapped[bool] = mapped_column(Boolean, default=False)
    __table_args__ = (CheckConstraint("role IN ('admin','recruiter','interviewer')"),)


class AuthSession(Base):
    __tablename__ = 'sessions'
    digest: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)


class Job(Base):
    __tablename__ = 'jobs'
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(120))
    department: Mapped[str] = mapped_column(String(80), index=True)
    location: Mapped[str] = mapped_column(String(100))
    openings: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default='open', index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    __table_args__ = (CheckConstraint('openings > 0'), CheckConstraint("status IN ('open','on_hold','closed')"))


class Candidate(Base):
    __tablename__ = 'candidates'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    phone: Mapped[str] = mapped_column(String(30), default='')
    source: Mapped[str] = mapped_column(String(20), index=True)
    notes: Mapped[str] = mapped_column(Text, default='')
    anonymized: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, index=True)


class CandidateTag(Base):
    __tablename__ = 'candidate_tags'
    candidate_id: Mapped[int] = mapped_column(ForeignKey('candidates.id', ondelete='CASCADE'), primary_key=True)
    tag: Mapped[str] = mapped_column(String(32), primary_key=True, index=True)


class Resume(Base):
    __tablename__ = 'resumes'
    candidate_id: Mapped[int] = mapped_column(ForeignKey('candidates.id', ondelete='CASCADE'), primary_key=True)
    content: Mapped[bytes] = mapped_column(LargeBinary)
    size: Mapped[int] = mapped_column(Integer)
    __table_args__ = (CheckConstraint('size > 0 AND size <= 1048576'),)


class Stage(Base):
    __tablename__ = 'stages'
    key: Mapped[str] = mapped_column(String(20), primary_key=True)
    label: Mapped[str] = mapped_column(String(50))
    position: Mapped[int] = mapped_column(Integer)


class RejectionReason(Base):
    __tablename__ = 'rejection_reasons'
    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(String(100), unique=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Criterion(Base):
    __tablename__ = 'criteria'
    key: Mapped[str] = mapped_column(String(20), primary_key=True)
    label: Mapped[str] = mapped_column(String(80))
    guidance: Mapped[str] = mapped_column(String(300), default='')


class Application(Base):
    __tablename__ = 'applications'
    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey('candidates.id', ondelete='CASCADE'), index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey('jobs.id'), index=True)
    stage: Mapped[str] = mapped_column(ForeignKey('stages.key'))
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    __table_args__ = (UniqueConstraint('candidate_id', 'job_id'), Index('ix_app_board', 'job_id', 'stage'))


class StageHistory(Base):
    __tablename__ = 'stage_history'
    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey('applications.id', ondelete='CASCADE'), index=True)
    from_stage: Mapped[str | None] = mapped_column(String(20))
    to_stage: Mapped[str] = mapped_column(ForeignKey('stages.key'), index=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=now, index=True)
    reason_id: Mapped[int | None] = mapped_column(ForeignKey('rejection_reasons.id'))


class Interview(Base):
    __tablename__ = 'interviews'
    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey('applications.id', ondelete='CASCADE'), index=True)
    interviewer_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    starts_at: Mapped[datetime] = mapped_column(DateTime)
    mode: Mapped[str] = mapped_column(String(20))
    created_by: Mapped[int] = mapped_column(ForeignKey('users.id'))
    __table_args__ = (Index('ix_interview_assignment', 'interviewer_id', 'starts_at'),)


class Scorecard(Base):
    __tablename__ = 'scorecards'
    id: Mapped[int] = mapped_column(primary_key=True)
    interview_id: Mapped[int] = mapped_column(ForeignKey('interviews.id', ondelete='CASCADE'), unique=True)
    submitted_by: Mapped[int] = mapped_column(ForeignKey('users.id'))
    technical: Mapped[int] = mapped_column(Integer)
    communication: Mapped[int] = mapped_column(Integer)
    culture: Mapped[int] = mapped_column(Integer)
    recommendation: Mapped[str] = mapped_column(String(20))
    feedback: Mapped[str] = mapped_column(Text)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    __table_args__ = (CheckConstraint('technical BETWEEN 1 AND 5 AND communication BETWEEN 1 AND 5 AND culture BETWEEN 1 AND 5'),)


class Offer(Base):
    __tablename__ = 'offers'
    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey('applications.id', ondelete='CASCADE'), unique=True)
    status: Mapped[str] = mapped_column(String(20))
    amount_minor: Mapped[int | None] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Activity(Base):
    __tablename__ = 'activity'
    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey('candidates.id', ondelete='CASCADE'), index=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    kind: Mapped[str] = mapped_column(String(40))
    summary: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Notification(Base):
    __tablename__ = 'notifications'
    id: Mapped[int] = mapped_column(primary_key=True)
    recipient_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    application_id: Mapped[int | None] = mapped_column(ForeignKey('applications.id', ondelete='CASCADE'))
    kind: Mapped[str] = mapped_column(String(40))
    message: Mapped[str] = mapped_column(String(200))
    read_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)