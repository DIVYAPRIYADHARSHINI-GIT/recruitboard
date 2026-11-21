from datetime import datetime
from fastapi import HTTPException
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError
from .models import Activity, Interview, Notification, User


def row(obj):
    if obj is None:
        return None
    if obj.__class__.__name__ in ('User', 'AuthSession', 'Resume'):
        raise ValueError('Sensitive model requires explicit serialization')
    result = {}
    for attr in inspect(obj).mapper.column_attrs:
        value = getattr(obj, attr.key)
        result[attr.key] = value.isoformat() + 'Z' if isinstance(value, datetime) else value
    return result


def commit(db, message='This record already exists. Refresh and try again.'):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, message)


def activity(db, candidate_id, actor_id, kind, summary):
    db.add(Activity(candidate_id=candidate_id, actor_id=actor_id, kind=kind, summary=summary))


def notify_team(db, application_id, kind, message, include_interviewers=False):
    recipients = set(db.scalars(select(User.id).where(User.active.is_(True), User.role.in_(['recruiter', 'admin']))))
    if include_interviewers:
        recipients.update(db.scalars(select(Interview.interviewer_id).where(Interview.application_id == application_id)))
    db.add_all([Notification(recipient_id=i, application_id=application_id, kind=kind, message=message) for i in recipients])