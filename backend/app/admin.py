from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, exists, select
from sqlalchemy.orm import Session
from . import schemas as s
from .common import commit, row
from .models import *
from .policy import assigned_application
from .security import admin, current_user, database, hasher, public_user

router = APIRouter()


@router.get('/users')
def users(user: User = Depends(admin), db: Session = Depends(database)):
    return [public_user(x) for x in db.scalars(select(User).order_by(User.id).limit(500))]


@router.post('/users', status_code=201)
def create_user(data: s.UserCreate, user: User = Depends(admin), db: Session = Depends(database)):
    item = User(name=data.name, email=data.email, role=data.role, password_hash=hasher.hash(data.password), active=True, demo=False)
    db.add(item)
    commit(db, 'An account with this email already exists.')
    return public_user(item)


@router.patch('/users/{user_id}')
def edit_user(user_id: int, data: s.UserUpdate, user: User = Depends(admin), db: Session = Depends(database)):
    item = db.get(User, user_id)
    if not item:
        raise HTTPException(404, 'User not found.')
    if item.id == user.id:
        raise HTTPException(422, 'Ask another admin to change your role or deactivate your account.')
    if item.demo:
        raise HTTPException(422, 'Built-in demo identities are protected so everyone can try each role.')
    item.role, item.active = data.role, data.active
    db.execute(delete(AuthSession).where(AuthSession.user_id == item.id))
    commit(db)
    return public_user(item)


@router.get('/settings')
def settings(user: User = Depends(current_user), db: Session = Depends(database)):
    return {'stages': [row(x) for x in db.scalars(select(Stage).order_by(Stage.position, Stage.key))], 'criteria': [row(x) for x in db.scalars(select(Criterion).order_by(Criterion.key))], 'rejection_reasons': [row(x) for x in db.scalars(select(RejectionReason).order_by(RejectionReason.id))]}


@router.put('/settings/stages/{key}')
def stage(key: s.StageKey, data: s.StageInput, user: User = Depends(admin), db: Session = Depends(database)):
    item = db.get(Stage, key)
    if not item:
        raise HTTPException(404, 'Stage not found.')
    item.label, item.position = data.label, data.position
    commit(db)
    return row(item)


@router.put('/settings/criteria/{key}')
def criterion(key: str, data: s.CriterionInput, user: User = Depends(admin), db: Session = Depends(database)):
    item = db.get(Criterion, key)
    if not item:
        raise HTTPException(404, 'Criterion not found.')
    item.label, item.guidance = data.label, data.guidance
    commit(db)
    return row(item)


@router.post('/settings/rejection-reasons', status_code=201)
def create_reason(data: s.ReasonInput, user: User = Depends(admin), db: Session = Depends(database)):
    item = RejectionReason(**data.model_dump())
    db.add(item)
    commit(db, 'This reason already exists.')
    return row(item)


@router.put('/settings/rejection-reasons/{reason_id}')
def reason(reason_id: int, data: s.ReasonInput, user: User = Depends(admin), db: Session = Depends(database)):
    item = db.get(RejectionReason, reason_id)
    if not item:
        raise HTTPException(404, 'Reason not found.')
    item.label, item.active = data.label, data.active
    commit(db)
    return row(item)


def notification_query(user):
    query = select(Notification).where(Notification.recipient_id == user.id)
    if user.role == 'interviewer':
        query = query.where(exists(select(Application.id).where(Application.id == Notification.application_id, assigned_application(user))))
    return query


@router.get('/notifications')
def notifications(user: User = Depends(current_user), db: Session = Depends(database)):
    return [row(x) for x in db.scalars(notification_query(user).order_by(Notification.created_at.desc(), Notification.id.desc()).limit(100))]


@router.post('/notifications/{notification_id}/read')
def read_notification(notification_id: int, user: User = Depends(current_user), db: Session = Depends(database)):
    item = db.scalar(notification_query(user).where(Notification.id == notification_id))
    if not item:
        raise HTTPException(404, 'Notification not found.')
    item.read_at = now()
    commit(db)
    return row(item)