import hashlib
import hmac
import secrets
import time
from collections import OrderedDict, deque
from datetime import timedelta
from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from .models import AuthSession, User, now

hasher = PasswordHasher()  # Argon2id defaults, independently salted.
COOKIE = 'rb_session'


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def csrf_for(sid):
    return hmac.new(sid.encode(), b'recruitboard-csrf-v1', hashlib.sha256).hexdigest()


def database(request: Request):
    with Session(request.app.state.engine, autoflush=False) as db:
        yield db


def session_record(request, db):
    sid = request.cookies.get(COOKIE, '')
    if len(sid) < 32 or len(sid) > 128:
        return None
    session = db.get(AuthSession, digest(sid))
    return session if session and session.expires_at > now() else None


def current_user(request: Request, db: Session = Depends(database)):
    session = session_record(request, db)
    user = db.get(User, session.user_id) if session and session.user_id else None
    if not user or not user.active:
        raise HTTPException(401, 'Please sign in to continue.')
    return user


def roles(*allowed):
    def check(user: User = Depends(current_user)):
        if user.role not in allowed:
            raise HTTPException(403, 'This action is not available for your role.')
        return user
    return check


recruiting = roles('admin', 'recruiter')
admin = roles('admin')


def public_user(user):
    return {'id': user.id, 'name': user.name, 'email': user.email, 'role': user.role, 'active': user.active, 'demo': user.demo}


def new_session(request, response, db, user_id=None):
    old = request.cookies.get(COOKIE)
    if old:
        db.execute(delete(AuthSession).where(AuthSession.digest == digest(old)))
    db.execute(delete(AuthSession).where(AuthSession.expires_at <= now()))
    sid = secrets.token_urlsafe(32)
    db.add(AuthSession(digest=digest(sid), user_id=user_id, expires_at=now()+timedelta(hours=8)))
    db.commit()
    response.set_cookie(COOKIE, sid, max_age=28800, httponly=True, secure=request.app.state.config.secure, samesite='lax', path='/')
    return csrf_for(sid)


def valid_password(encoded, supplied):
    try:
        return hasher.verify(encoded, supplied)
    except (VerificationError, InvalidHashError):
        return False


class Limiter:
    """Single-worker fixed-window counters. Bounded keys; fail closed on capacity."""
    def __init__(self):
        self.events = OrderedDict()

    def allow(self, key, limit, window=60):
        t = time.monotonic()
        for old_key in list(self.events):
            if self.events[old_key][-1] <= t - 900:
                del self.events[old_key]
        if key not in self.events and len(self.events) >= 10000:
            return False
        queue = self.events.setdefault(key, deque())
        while queue and queue[0] <= t-window:
            queue.popleft()
        if len(queue) >= limit:
            return False
        queue.append(t)
        return True


def unsafe_request_error(request):
    if request.method in ('GET', 'HEAD', 'OPTIONS'):
        return None
    config = request.app.state.config
    if request.headers.get('origin') not in config.origins:
        return (403, 'Request origin is not allowed.')
    ip = request.client.host if request.client else 'unknown'
    login = request.url.path in ('/api/auth/login', '/api/auth/demo')
    if not request.app.state.limiter.allow(('login' if login else 'write', ip), config.login_limit if login else config.write_limit, 900 if login else 60):
        return (429, 'Too many requests. Please wait before trying again.')
    sid = request.cookies.get(COOKIE, '')
    if not sid or not hmac.compare_digest(request.headers.get('x-csrf-token', ''), csrf_for(sid)):
        return (403, 'Security check expired. Refresh and try again.')
    with Session(request.app.state.engine) as db:
        if not session_record(request, db):
            return (403, 'Security check expired. Refresh and try again.')
    return None