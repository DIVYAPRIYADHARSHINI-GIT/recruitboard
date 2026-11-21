import os
from pathlib import Path
import subprocess
import sys
from app.deployment import PUBLIC_VERCEL_DEFAULTS, configure_vercel_defaults


def test_public_defaults_are_complete_and_secret_free():
    values = {}
    configure_vercel_defaults(values)
    assert values == PUBLIC_VERCEL_DEFAULTS
    assert values['APP_ENV'] == 'production'
    assert values['COOKIE_SECURE'] == 'true'
    assert values['ALLOWED_ORIGINS'] == 'https://recruitboard-pi.vercel.app'
    assert values['DEMO_MODE'] == values['SEED_DEMO'] == 'true'
    assert 'DATABASE_URL' not in values and 'SESSION_SECRET' not in values


def test_explicit_operator_settings_and_private_input_are_not_overwritten():
    values = {'DATABASE_URL': 'TEST_SENTINEL_NOT_A_CONNECTION', 'DEMO_MODE': 'false', 'SEED_DEMO': 'false', 'ALLOWED_ORIGINS': 'https://private.example.invalid'}
    original = dict(values)
    configure_vercel_defaults(values)
    assert all(values[k] == v for k, v in original.items())


def test_defaults_are_idempotent_and_do_not_modify_global_env_when_given_mapping():
    before = os.environ.get('ALLOWED_ORIGINS')
    values = {}
    configure_vercel_defaults(values)
    first = dict(values)
    configure_vercel_defaults(values)
    assert values == first
    assert os.environ.get('ALLOWED_ORIGINS') == before


def test_real_entrypoint_boots_with_isolated_local_database(tmp_path):
    # Fresh interpreter reproduces entrypoint import order. Force a LOCAL SQLite
    # development fixture; never inherit or contact a production database.
    environment = dict(os.environ)
    for key in PUBLIC_VERCEL_DEFAULTS:
        environment.pop(key, None)
    environment.update(APP_ENV='development', DATABASE_URL=f'sqlite:///{tmp_path}/wrapper.db', ALLOWED_ORIGINS='https://testserver')
    script = '''
from fastapi.testclient import TestClient
from vercel_entry import app
with TestClient(app, base_url='https://testserver', headers={'Origin': 'https://testserver'}) as client:
    assert client.get('/health').json() == {'status': 'ok'}
    session = client.get('/api/auth/session').json()
    assert session['demo'] is True
    response = client.post('/api/auth/demo', json={'role': 'recruiter'}, headers={'X-CSRF-Token': session['csrf']})
    assert response.status_code == 200
    assert len(client.get('/api/jobs').json()) == 5
print('Vercel entrypoint local startup and demo login passed; no secrets printed.')
'''
    result = subprocess.run([sys.executable, '-c', script], cwd=Path(__file__).resolve().parents[1], env=environment, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, 'Isolated entrypoint startup failed; no environment values are exposed.'
    assert 'local startup and demo login passed' in result.stdout