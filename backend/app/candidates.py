from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import delete, exists, func, select, update
from sqlalchemy.orm import Session
from . import schemas as s
from .common import activity, commit, row
from .models import *
from .policy import assigned_application, candidate_or_404, visible_candidate
from .security import admin, current_user, database, recruiting

router = APIRouter()


def candidate_summary(db, user, candidate):
    result = row(candidate)
    result['tags'] = list(db.scalars(select(CandidateTag.tag).where(CandidateTag.candidate_id == candidate.id)))
    query = select(Application, Job.title).join(Job).where(Application.candidate_id == candidate.id)
    if user.role == 'interviewer':
        query = query.where(assigned_application(user))
    result['applications'] = [{**row(a), 'job_title': title} for a, title in db.execute(query)]
    result['has_resume'] = bool(db.scalar(select(Resume.candidate_id).where(Resume.candidate_id == candidate.id)))
    return result


@router.get('/candidates')
def candidates(q: str = Query('', max_length=100), job: int | None = Query(None, gt=0), stage: s.StageKey | None = None, source: s.Source | None = None, tag: str = Query('', max_length=32), interviewer: int | None = Query(None, gt=0), sort: Literal['newest', 'oldest', 'name'] = 'newest', page: int = Query(1, ge=1, le=100000), size: int = Query(20, ge=1, le=50), user: User = Depends(current_user), db: Session = Depends(database)):
    query = select(Candidate)
    if user.role == 'interviewer':
        query = query.where(visible_candidate(user))
    if q:
        escaped = q.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
        query = query.where(Candidate.name.ilike(f'%{escaped}%', escape='\\') | Candidate.email.ilike(f'%{escaped}%', escape='\\'))
    if source:
        query = query.where(Candidate.source == source)
    if tag:
        query = query.where(exists(select(CandidateTag.candidate_id).where(CandidateTag.candidate_id == Candidate.id, CandidateTag.tag == tag.lower())))
    if job or stage or interviewer:
        applications = select(Application.id).where(Application.candidate_id == Candidate.id)
        if user.role == 'interviewer':
            applications = applications.where(assigned_application(user))
        if job:
            applications = applications.where(Application.job_id == job)
        if stage:
            applications = applications.where(Application.stage == stage)
        if interviewer:
            if user.role == 'interviewer' and interviewer != user.id:
                return {'items': [], 'total': 0, 'page': page, 'size': size}
            applications = applications.where(exists(select(Interview.id).where(Interview.application_id == Application.id, Interview.interviewer_id == interviewer)))
        query = query.where(exists(applications))
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    ordering = {'newest': Candidate.created_at.desc(), 'oldest': Candidate.created_at.asc(), 'name': Candidate.name.asc()}[sort]
    items = db.scalars(query.order_by(ordering, Candidate.id).offset((page-1)*size).limit(size)).all()
    return {'items': [candidate_summary(db, user, c) for c in items], 'total': total, 'page': page, 'size': size}


@router.get('/candidates/{candidate_id}')
def profile(candidate_id: int, user: User = Depends(current_user), db: Session = Depends(database)):
    candidate = candidate_or_404(db, user, candidate_id)
    result = candidate_summary(db, user, candidate)
    app_ids = [a['id'] for a in result['applications']]
    query = select(Interview, User.name).join(User, Interview.interviewer_id == User.id).where(Interview.application_id.in_(app_ids))
    if user.role == 'interviewer':
        query = query.where(Interview.interviewer_id == user.id)
    interviews = [{**row(i), 'interviewer_name': name, 'scorecard': row(db.scalar(select(Scorecard).where(Scorecard.interview_id == i.id)))} for i, name in db.execute(query.order_by(Interview.starts_at.desc()))]
    result['interviews'] = interviews
    result['offers'] = [] if user.role == 'interviewer' else [row(x) for x in db.scalars(select(Offer).where(Offer.application_id.in_(app_ids)))]
    result['history'] = [{**row(h), 'actor_name': name} for h, name in db.execute(select(StageHistory, User.name).join(User, StageHistory.actor_id == User.id).where(StageHistory.application_id.in_(app_ids)).order_by(StageHistory.occurred_at.desc(), StageHistory.id.desc()))]
    result['timeline'] = [] if user.role == 'interviewer' else [{**row(a), 'actor_name': name} for a, name in db.execute(select(Activity, User.name).join(User, Activity.actor_id == User.id).where(Activity.candidate_id == candidate.id).order_by(Activity.created_at.desc(), Activity.id.desc()).limit(200))]
    return result


def set_tags(db, candidate_id, tags):
    db.execute(delete(CandidateTag).where(CandidateTag.candidate_id == candidate_id))
    db.add_all(CandidateTag(candidate_id=candidate_id, tag=t) for t in sorted({x.lower() for x in tags}))


def add_application(db, candidate_id, job_id, actor_id):
    job = db.get(Job, job_id)
    if not job or job.status != 'open':
        raise HTTPException(422, 'Choose an open job for this application.')
    application = Application(candidate_id=candidate_id, job_id=job_id, stage='applied')
    db.add(application)
    try:
        db.flush()
    except Exception as error:
        from sqlalchemy.exc import IntegrityError
        if isinstance(error, IntegrityError):
            db.rollback()
            raise HTTPException(409, 'This candidate already has an application for this job.')
        raise
    db.add(StageHistory(application_id=application.id, from_stage=None, to_stage='applied', actor_id=actor_id))
    activity(db, candidate_id, actor_id, 'application', 'Application created in Applied')
    return application


@router.post('/candidates', status_code=201)
def create_candidate(data: s.CandidateCreate, user: User = Depends(recruiting), db: Session = Depends(database)):
    if db.scalar(select(Candidate.id).where(Candidate.email == data.email)):
        raise HTTPException(409, 'A candidate with this email already exists. Find their profile instead of creating a duplicate.')
    candidate = Candidate(**data.model_dump(exclude={'job_id', 'tags'}))
    db.add(candidate)
    try:
        db.flush()
    except Exception as error:
        from sqlalchemy.exc import IntegrityError
        if isinstance(error, IntegrityError):
            db.rollback()
            raise HTTPException(409, 'A candidate with this email already exists.')
        raise
    set_tags(db, candidate.id, data.tags)
    add_application(db, candidate.id, data.job_id, user.id)
    commit(db)
    return candidate_summary(db, user, candidate)


@router.put('/candidates/{candidate_id}')
def edit_candidate(candidate_id: int, data: s.CandidateInput, user: User = Depends(recruiting), db: Session = Depends(database)):
    candidate = candidate_or_404(db, user, candidate_id)
    if candidate.anonymized:
        raise HTTPException(409, 'An anonymized profile cannot be restored or edited.')
    for key, value in data.model_dump(exclude={'tags'}).items():
        setattr(candidate, key, value)
    set_tags(db, candidate_id, data.tags)
    activity(db, candidate_id, user.id, 'profile', 'Profile details or notes updated')
    commit(db, 'A candidate with this email already exists.')
    return candidate_summary(db, user, candidate)


@router.get('/candidates/{candidate_id}/resume')
def download_resume(candidate_id: int, user: User = Depends(current_user), db: Session = Depends(database)):
    candidate_or_404(db, user, candidate_id)
    resume = db.get(Resume, candidate_id)
    if not resume:
        raise HTTPException(404, 'No resume has been uploaded.')
    return Response(resume.content, media_type='application/pdf', headers={'Content-Disposition': 'attachment; filename="resume.pdf"', 'Content-Security-Policy': "sandbox; default-src 'none'", 'X-Content-Type-Options': 'nosniff'})


@router.put('/candidates/{candidate_id}/resume')
async def upload_resume(candidate_id: int, request: Request, user: User = Depends(recruiting), db: Session = Depends(database)):
    candidate = candidate_or_404(db, user, candidate_id)
    if candidate.anonymized:
        raise HTTPException(409, 'Anonymized profiles cannot accept resumes.')
    filename = request.headers.get('x-filename', '')
    if request.headers.get('content-type', '').split(';')[0].lower() != 'application/pdf' or not filename.lower().endswith('.pdf') or len(filename) > 200:
        raise HTTPException(415, 'Upload one PDF (.pdf, application/pdf) of at most 1 MB.')
    content = bytearray()
    async for chunk in request.stream():
        if len(content)+len(chunk) > 1048576:
            raise HTTPException(413, 'PDF must be at most 1 MB (1,048,576 bytes).')
        content.extend(chunk)
    if not content.startswith(b'%PDF-') or b'%%EOF' not in content[-2048:]:
        raise HTTPException(415, 'This file does not have a valid PDF signature and ending.')
    resume = db.get(Resume, candidate_id)
    if resume:
        resume.content, resume.size = bytes(content), len(content)
    else:
        db.add(Resume(candidate_id=candidate_id, content=bytes(content), size=len(content)))
    activity(db, candidate_id, user.id, 'resume', 'Resume uploaded or replaced')
    commit(db)
    return {'ok': True, 'size': len(content)}


@router.delete('/candidates/{candidate_id}/resume')
def delete_resume(candidate_id: int, user: User = Depends(recruiting), db: Session = Depends(database)):
    candidate_or_404(db, user, candidate_id)
    db.execute(delete(Resume).where(Resume.candidate_id == candidate_id))
    activity(db, candidate_id, user.id, 'resume', 'Resume removed')
    commit(db)
    return {'ok': True}


@router.post('/candidates/{candidate_id}/privacy')
def privacy(candidate_id: int, data: s.PrivacyInput, user: User = Depends(admin), db: Session = Depends(database)):
    candidate = candidate_or_404(db, user, candidate_id)
    if data.action == 'delete':
        db.delete(candidate)
    else:
        candidate.name = 'Anonymized candidate'
        candidate.email = f'anonymized-{candidate.id}@example.invalid'
        candidate.phone = ''
        candidate.notes = ''
        candidate.anonymized = True
        db.execute(delete(Resume).where(Resume.candidate_id == candidate_id))
        db.execute(delete(CandidateTag).where(CandidateTag.candidate_id == candidate_id))
        interview_ids = select(Interview.id).join(Application).where(Application.candidate_id == candidate_id)
        db.execute(update(Scorecard).where(Scorecard.interview_id.in_(interview_ids)).values(feedback='Removed for privacy'))
        db.execute(delete(Activity).where(Activity.candidate_id == candidate_id))
        activity(db, candidate_id, user.id, 'privacy', 'Identifying information permanently anonymized')
    commit(db)
    return {'ok': True, 'action': data.action}