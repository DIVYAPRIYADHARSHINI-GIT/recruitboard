from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
from sqlalchemy import text
from .config import Config
from .db import initialize, make_engine
from .security import Limiter, unsafe_request_error


def create_app(config=None):
    config = config or Config()
    config.validate()
    engine = make_engine(config.database_url)

    @asynccontextmanager
    async def lifespan(app):
        try:
            initialize(engine, seed=config.seed)
        except Exception:
            # Driver exception text may contain a database address. Never propagate it.
            raise RuntimeError('Database initialization failed. Verify the database and migration settings in the hosting dashboard.') from None
        yield
        engine.dispose()

    app = FastAPI(title='RecruitBoard API', version='1.0.0', lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.engine = engine
    app.state.config = config
    app.state.limiter = Limiter()
    app.add_middleware(CORSMiddleware, allow_origins=list(config.origins), allow_credentials=True, allow_methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'], allow_headers=['Content-Type', 'X-CSRF-Token'])

    @app.middleware('http')
    async def security_headers(request: Request, call_next):
        try:
            content_length = int(request.headers.get('content-length', '0') or 0)
        except ValueError:
            content_length = 1100001
        if content_length > 1100000:
            response = JSONResponse({'detail': 'Request is too large. PDFs must be at most 1 MB.'}, status_code=413)
        else:
            try:
                error = unsafe_request_error(request)
                response = JSONResponse({'detail': error[1]}, status_code=error[0], headers={'Retry-After': '60'} if error[0] == 429 else {}) if error else await call_next(request)
            except Exception as error:
                import logging
                logging.getLogger('recruitboard').error('Request failed: %s', type(error).__name__)
                response = JSONResponse({'detail': 'The service could not complete this request. Please try again.'}, status_code=500)
        response.headers['Cache-Control'] = 'no-store, private'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['X-Frame-Options'] = 'DENY'
        if config.secure:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000'
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, error):
        # Pydantic's default response includes input values; do not echo private inputs.
        return JSONResponse({'detail': 'Please check the field formats, required values and limits.'}, status_code=422)

    @app.get('/health')
    def health():
        try:
            with engine.connect() as db:
                ok = db.scalar(text('SELECT 1')) == 1
            return {'status': 'ok' if ok else 'unavailable'}
        except Exception:
            return JSONResponse({'status': 'unavailable'}, status_code=503)

    from .auth import router as auth_router
    app.include_router(auth_router, prefix='/api')
    from .candidates import router as candidate_router
    from .workflow import router as workflow_router
    from .admin import router as admin_router
    from .reports import router as report_router
    for router in (candidate_router, workflow_router, admin_router, report_router):
        app.include_router(router, prefix='/api')
    return app


app = create_app()