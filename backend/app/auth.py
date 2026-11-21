from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from . import schemas as s
from .models import AuthSession, User
from .security import COOKIE, csrf_for, current_user, database, digest, hasher, new_session, public_user, session_record, valid_password

router = APIRouter()
# Equal work for nonexistent users; the generated dummy hash is never serialized.
_dummy = hasher.hash('not-a-login-identity')


@router.get('/auth/session')
def bootstrap(request: Request, response: Response, db: Session = Depends(database)):
    record = session_record(request, db)
    user = db.get(User, record.user_id) if record and record.user_id else None
    if record and (user is None or user.active):
        csrf = csrf_for(request.cookies[COOKIE])
    else:
        ip = request.client.host if request.client else 'unknown'
        if not request.app.state.limiter.allow(('bootstrap', ip), 60):
            raise HTTPException(429, 'Please wait before refreshing again.')
        csrf = new_session(request, response, db)
        user = None
    return {'user': public_user(user) if user else None, 'csrf': csrf, 'demo': request.app.state.config.demo}


@router.post('/auth/login')
def login(data: s.Login, request: Request, response: Response, db: Session = Depends(database)):
    user = db.scalar(select(User).where(User.email == data.email))
    valid = valid_password(user.password_hash if user else _dummy, data.password)
    if not user or not user.active or user.demo or not valid:
        raise HTTPException(401, 'Email or password is incorrect.')
    csrf = new_session(request, response, db, user.id)
    return {'user': public_user(user), 'csrf': csrf, 'demo': request.app.state.config.demo}


@router.post('/auth/demo')
def demo(data: s.Demo, request: Request, response: Response, db: Session = Depends(database)):
    if not request.app.state.config.demo:
        raise HTTPException(404, 'Demo is not enabled.')
    user = db.scalar(select(User).where(User.email == f'{data.role}@recruitboard.example', User.demo.is_(True), User.active.is_(True), User.role == data.role))
    if not user:
        raise HTTPException(503, 'The demo is not initialized yet.')
    return {'user': public_user(user), 'csrf': new_session(request, response, db, user.id), 'demo': True}


@router.post('/auth/logout')
def logout(request: Request, response: Response, user: User = Depends(current_user), db: Session = Depends(database)):
    db.execute(delete(AuthSession).where(AuthSession.digest == digest(request.cookies.get(COOKIE, ''))))
    db.commit()
    response.delete_cookie(COOKIE, path='/', secure=request.app.state.config.secure, httponly=True, samesite='lax')
    return {'ok': True}