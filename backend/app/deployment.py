"""Explicit PUBLIC defaults for this approved Vercel shared-demo deployment.

No database address or secret belongs here. Explicit dashboard settings win.
Generic app.main/local/private installations do not call this automatically.
"""
import os
from collections.abc import MutableMapping

PUBLIC_VERCEL_DEFAULTS = {
    'APP_ENV': 'production',
    'COOKIE_SECURE': 'true',
    'DEMO_MODE': 'true',
    'SEED_DEMO': 'true',
    'ALLOWED_ORIGINS': 'https://recruitboard-pi.vercel.app',
    'LOGIN_LIMIT': '10',
    'WRITE_LIMIT': '120',
}


def configure_vercel_defaults(environ: MutableMapping[str, str] | None = None):
    target = os.environ if environ is None else environ
    for key, value in PUBLIC_VERCEL_DEFAULTS.items():
        target.setdefault(key, value)