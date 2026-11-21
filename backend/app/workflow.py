from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, select, update
from sqlalchemy.orm import Session
from . import schemas as s
from .candidates import add_application
from .common import activity, commit, notify_team, row
from .models import *
from .policy import application_or_404, assigned_application, candidate_or_404, interview_or_404
from .security import current_user, database, recruiting, roles

router = APIRouter()


@router.get('/jobs')
def jobs(user: User = Depends(current_user), db: Session = Depends(database)):
    counts = select(Application.job_id, func.count().label('candidates'), func.sum(case((Application.stage == 'hired', 1), else_=0)).label('filled')).group_by(Application.job_id)
    if user.role == 'interviewer':
        counts = counts.where(assigned_application(user))
    counts = counts.subquery()
    query = select(Job, func.coalesce(counts.c.candidates, 0), func.coalesce(counts.c.filled, 0)).outerjoin(counts, counts.c.job_id == Job.id)
    if user.role == 'interviewer':
        query = query.where(counts.c.candidates > 0)
    return [{**row(j), 'candidates': c, 'filled': f} for j, c, f in db.execute(query.order_by(Job.id))]


@router.post('/jobs', status_code=201)
def create_job(data: s.JobInput, user: User = Depends(recruiting), db: Session = Depends(database)):
    item = Job(**data.model_dump())
    db.add(item)
    commit(db)
    return row(item)


@router.put('/jobs/{job_id}')
def edit_job(job_id: int, data: s.JobInput, user: User = Depends(recruiting), db: Session = Depends(database)):
    item = db.get(Job, job_id)
    if not item:
        raise HTTPException(404, 'Job not found.')
    for key, value in data.model_dump().items():
        setattr(item, key, value)
    commit(db)
    return row(item)


@router.get('/jobs/{job_id}/board')
def board(job_id: int, user: User = Depends(recruiting), db: Session = Depends(database)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(404, 'Job not found.')
    items = [{**row(a), 'name': c.name, 'email': c.email, 'source': c.source, 'tags': list(db.scalars(select(CandidateTag.tag).where(CandidateTag.candidate_id == c.id)))} for a, c in db.execute(select(Application, Candidate).join(Candidate).where(Application.job_id == job_id).order_by(Application.created_at.desc()).limit(500))]
    counts = dict(db.execute(select(Application.stage, func.count()).where(Application.job_id == job_id).group_by(Application.stage)).all())
    return {'job': row(job), 'items': items, 'counts': counts, 'limited': sum(counts.values()) > 500}


@router.post('/applications', status_code=201)
def create_application(data: s.ApplicationInput, user: User = Depends(recruiting), db: Session = Depends(database)):
    candidate = candidate_or_404(db, user, data.candidate_id)
    if candidate.anonymized:
        raise HTTPException(409, 'Cannot add an anonymized candidate to a job.')
    item = add_application(db, data.candidate_id, data.job_id, user.id)
    commit(db)
    return row(item)


@router.get('/applications/{application_id}')
def get_application(application_id: int, user: User = Depends(current_user), db: Session = Depends(database)):
    return row(application_or_404(db, user, application_id))


@router.get('/applications/{application_id}/history')
def history(application_id: int, user: User = Depends(current_user), db: Session = Depends(database)):
    application_or_404(db, user, application_id)
    return [row(x) for x in db.scalars(select(StageHistory).where(StageHistory.application_id == application_id).order_by(StageHistory.occurred_at, StageHistory.id))]


@router.post('/applications/{application_id}/stage')
def move(application_id: int, data: s.Move, user: User = Depends(recruiting), db: Session = Depends(database)):
    item = application_or_404(db, user, application_id)
    if data.version != item.version:
        raise HTTPException(409, 'This application changed. Refresh before moving it again.')
    if data.stage == item.stage:
        return row(item)
    if data.stage == 'rejected':
        reason = db.get(RejectionReason, data.reason_id) if data.reason_id else None
        if not reason or not reason.active:
            raise HTTPException(422, 'Select an active rejection reason before confirming.')
    elif data.reason_id:
        raise HTTPException(422, 'Rejection reasons apply only to Rejected.')
    previous = item.stage
    changed = db.execute(update(Application).where(Application.id == item.id, Application.version == data.version).values(stage=data.stage, version=data.version+1))
    if changed.rowcount != 1:
        db.rollback()
        raise HTTPException(409, 'Another person moved this application. Refresh and try again.')
    db.add(StageHistory(application_id=item.id, from_stage=previous, to_stage=data.stage, actor_id=user.id, reason_id=data.reason_id))
    activity(db, item.candidate_id, user.id, 'stage', f'Application moved from {previous.title()} to {data.stage.title()}')
    notify_team(db, item.id, 'stage', f'An application moved to {data.stage.title()}.', True)
    commit(db)
    db.refresh(item)
    return row(item)


@router.get('/interviewers')
def interviewers(user: User = Depends(recruiting), db: Session = Depends(database)):
    return [{'id': u.id, 'name': u.name} for u in db.scalars(select(User).where(User.role == 'interviewer', User.active.is_(True)).order_by(User.name))]


def interview_data(db, item):
    application = db.get(Application, item.application_id)
    candidate = db.get(Candidate, application.candidate_id)
    job = db.get(Job, application.job_id)
    return {**row(item), 'candidate_id': candidate.id, 'candidate_name': candidate.name, 'job_title': job.title, 'interviewer_name': db.get(User, item.interviewer_id).name, 'scorecard': row(db.scalar(select(Scorecard).where(Scorecard.interview_id == item.id)))}


@router.get('/interviews')
def interviews(page: int = Query(1, ge=1), size: int = Query(30, ge=1, le=100), user: User = Depends(current_user), db: Session = Depends(database)):
    query = select(Interview)
    if user.role == 'interviewer':
        query = query.where(Interview.interviewer_id == user.id)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    return {'items': [interview_data(db, i) for i in db.scalars(query.order_by(Interview.starts_at.desc()).offset((page-1)*size).limit(size))], 'total': total}


@router.get('/interviews/{interview_id}')
def interview(interview_id: int, user: User = Depends(current_user), db: Session = Depends(database)):
    return interview_data(db, interview_or_404(db, user, interview_id))


@router.post('/interviews', status_code=201)
def schedule(data: s.InterviewInput, user: User = Depends(recruiting), db: Session = Depends(database)):
    application = application_or_404(db, user, data.application_id)
    candidate = db.get(Candidate, application.candidate_id)
    if candidate.anonymized:
        raise HTTPException(409, 'Cannot schedule an anonymized candidate.')
    interviewer = db.get(User, data.interviewer_id)
    if not interviewer or interviewer.role != 'interviewer' or not interviewer.active:
        raise HTTPException(422, 'Choose an active interviewer.')
    item = Interview(**data.model_dump(), created_by=user.id)
    db.add(item)
    db.add(Notification(recipient_id=interviewer.id, application_id=application.id, kind='assignment', message='An interview has been assigned to you.'))
    activity(db, application.candidate_id, user.id, 'interview', 'Interview scheduled')
    commit(db)
    return interview_data(db, item)


@router.get('/interviews/{interview_id}/scorecard')
def scorecard(interview_id: int, user: User = Depends(current_user), db: Session = Depends(database)):
    interview_or_404(db, user, interview_id)
    item = db.scalar(select(Scorecard).where(Scorecard.interview_id == interview_id))
    if not item:
        raise HTTPException(404, 'No scorecard submitted yet.')
    return row(item)


@router.post('/interviews/{interview_id}/scorecard', status_code=201)
def submit_scorecard(interview_id: int, data: s.ScoreInput, user: User = Depends(roles('interviewer')), db: Session = Depends(database)):
    item = interview_or_404(db, user, interview_id)
    application = db.get(Application, item.application_id)
    if db.get(Candidate, application.candidate_id).anonymized:
        raise HTTPException(409, 'This candidate has been anonymized.')
    card = Scorecard(interview_id=item.id, submitted_by=user.id, **data.model_dump())
    db.add(card)
    activity(db, application.candidate_id, user.id, 'scorecard', 'Interview scorecard submitted')
    notify_team(db, application.id, 'scorecard', 'A new scorecard is ready to review.')
    commit(db, 'A scorecard has already been submitted for this interview.')
    return row(card)


@router.get('/applications/{application_id}/offer')
def get_offer(application_id: int, user: User = Depends(recruiting), db: Session = Depends(database)):
    application_or_404(db, user, application_id)
    return row(db.scalar(select(Offer).where(Offer.application_id == application_id)))


@router.put('/applications/{application_id}/offer')
def offer(application_id: int, data: s.OfferInput, user: User = Depends(recruiting), db: Session = Depends(database)):
    application = application_or_404(db, user, application_id)
    if db.get(Candidate, application.candidate_id).anonymized:
        raise HTTPException(409, 'Cannot create offers for an anonymized candidate.')
    item = db.scalar(select(Offer).where(Offer.application_id == application_id).with_for_update())
    if item:
        allowed = {'draft': {'draft', 'sent'}, 'sent': {'sent', 'accepted', 'declined'}, 'accepted': {'accepted'}, 'declined': {'declined'}}
        if data.status not in allowed[item.status]:
            raise HTTPException(422, 'Offers move from draft to sent, then accepted or declined.')
        if item.status != 'draft' and item.amount_minor != data.amount_minor:
            raise HTTPException(422, 'The fictional amount cannot change after an offer is sent.')
        item.status, item.amount_minor, item.updated_at = data.status, data.amount_minor, now()
    else:
        if data.status != 'draft':
            raise HTTPException(422, 'Create a draft before sending an offer.')
        item = Offer(application_id=application_id, **data.model_dump())
        db.add(item)
    activity(db, application.candidate_id, user.id, 'offer', f'Offer recorded as {data.status}')
    commit(db)
    return row(item)