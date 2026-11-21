from fastapi import HTTPException
from sqlalchemy import exists, select
from .models import Application, Candidate, Interview


def assigned_application(user):
    return exists(select(Interview.id).where(Interview.application_id == Application.id, Interview.interviewer_id == user.id))


def visible_candidate(user):
    return exists(select(Application.id).where(Application.candidate_id == Candidate.id, assigned_application(user)))


def candidate_or_404(db, user, candidate_id):
    query = select(Candidate).where(Candidate.id == candidate_id)
    if user.role == 'interviewer':
        query = query.where(visible_candidate(user))
    candidate = db.scalar(query)
    if not candidate:
        raise HTTPException(404, 'Candidate not found.')
    return candidate


def application_or_404(db, user, application_id):
    query = select(Application).where(Application.id == application_id)
    if user.role == 'interviewer':
        query = query.where(assigned_application(user))
    item = db.scalar(query)
    if not item:
        raise HTTPException(404, 'Application not found.')
    return item


def interview_or_404(db, user, interview_id):
    query = select(Interview).where(Interview.id == interview_id)
    if user.role == 'interviewer':
        query = query.where(Interview.interviewer_id == user.id)
    item = db.scalar(query)
    if not item:
        raise HTTPException(404, 'Interview not found.')
    return item