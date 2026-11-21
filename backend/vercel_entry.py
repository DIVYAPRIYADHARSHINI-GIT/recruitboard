"""Vercel ASGI entrypoint; apply public settings BEFORE app construction."""
from app.deployment import configure_vercel_defaults

configure_vercel_defaults()

# DATABASE_URL is supplied only by Vercel's private Production environment.
from app.main import app  # noqa: E402, F401