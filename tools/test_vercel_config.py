"""Offline Vercel Services configuration checks; never fetches account secrets."""
import json
from pathlib import Path
import pytest
from jsonschema.validators import validator_for

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / 'vercel.json').read_text())


def test_only_frontend_and_backend_services():
    assert set(CONFIG['services']) == {'frontend', 'backend'}
    assert CONFIG['services']['frontend']['root'] == 'frontend/'
    assert CONFIG['services']['backend']['root'] == 'backend/'
    assert CONFIG['services']['backend']['entrypoint'] == 'vercel_entry:app'
    assert CONFIG['regions'] == ['sin1']


def test_static_build_and_spa_fallback():
    frontend = CONFIG['services']['frontend']
    assert frontend['framework'] == 'vite'
    assert frontend['installCommand'] == 'npm ci --no-audit --no-fund'
    assert frontend['buildCommand'] == 'npm run build'
    assert frontend['outputDirectory'] == 'dist'
    assert frontend['rewrites'] == [{'source': '/(.*)', 'destination': '/index.html'}]


def test_same_origin_api_and_health_route_before_frontend():
    assert CONFIG['rewrites'] == [
        {'source': '/api/(.*)', 'destination': {'service': 'backend'}},
        {'source': '/health', 'destination': {'service': 'backend'}},
        {'source': '/(.*)', 'destination': {'service': 'frontend'}},
    ]
    # Destination path is deliberately omitted so the API sees its original /api/* path.
    assert all('path' not in item['destination'] for item in CONFIG['rewrites'])


def test_function_duration_and_migrations_bundled():
    function = CONFIG['services']['backend']['functions']['vercel_entry.py']
    assert CONFIG['services']['backend']['framework'] == 'fastapi'
    assert function['maxDuration'] == 60
    assert 'migrations/**' in function['includeFiles'] and 'alembic.ini' in function['includeFiles']


def test_supported_pinned_runtimes():
    assert (ROOT / 'backend/.python-version').read_text().strip() == '3.14'
    assert (ROOT / 'frontend/.nvmrc').read_text().strip() == '22.22.0'
    assert json.loads((ROOT / 'frontend/package.json').read_text())['engines']['node'] == '22.x'


def test_sensitive_and_large_local_files_excluded_from_upload():
    excluded = set((ROOT / '.vercelignore').read_text().splitlines())
    assert {'.env*', '**/.env*', '.vercel/', '.cache/', '.browser/', '.test-data/', '**/.venv*/', '**/*.db', 'screenshots/', 'bugs/', 'evidence/', '*.pdf'} <= excluded
    assert 'env' not in CONFIG  # Public defaults are applied by the dedicated ASGI entrypoint.
    entrypoint = (ROOT / 'backend/vercel_entry.py').read_text()
    assert entrypoint.index('configure_vercel_defaults()') < entrypoint.index('from app.main import app')
    assert 'builds' not in CONFIG  # Use the supported Services model, not mixed legacy builders.
    assert 'onrender.com' not in json.dumps(CONFIG)
    assert 'netlify' not in json.dumps(CONFIG)


def test_same_origin_csp_and_safe_headers():
    headers = {h['key']: h['value'] for h in CONFIG['headers'][0]['headers']}
    assert headers['X-Content-Type-Options'] == 'nosniff'
    assert headers['X-Frame-Options'] == 'DENY'
    assert "connect-src 'self'" in headers['Content-Security-Policy']


def test_against_official_vercel_schema():
    path = ROOT / '.cache/vercel-docs/vercel.schema.json'
    if not path.exists():
        pytest.skip('Official public schema not cached; this test never fetches the network.')
    schema = json.loads(path.read_text())
    # Published schema declares draft-04 but uses numeric exclusiveMinimum and const.
    # Those are draft-06+ semantics. Correct only the dialect marker, not constraints;
    # retain the downloaded original and the original failed-check transcript.
    assert schema['$schema'] == 'http://json-schema.org/draft-04/schema#'
    compatible = {**schema, '$schema': 'http://json-schema.org/draft-07/schema#'}
    validator = validator_for(compatible)
    validator.check_schema(compatible)
    validator(compatible).validate(CONFIG)
