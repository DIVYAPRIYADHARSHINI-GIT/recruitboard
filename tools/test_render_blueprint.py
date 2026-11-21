"""Offline checks: no Render account, deployed app or database is contacted.

If the official public schema was downloaded to .cache/render-docs, validate
against it too. Install tools/requirements.txt in the project-local venv first.
"""
import ast
import json
from pathlib import Path

import pytest
import yaml
from jsonschema.validators import validator_for

ROOT = Path(__file__).resolve().parents[1]
BLUEPRINT = yaml.safe_load((ROOT / 'render.yaml').read_text())
SERVICE = BLUEPRINT['services'][0]
ENV = {entry['key']: entry for entry in SERVICE['envVars']}


def test_exactly_one_free_web_service_without_database():
    assert set(BLUEPRINT) == {'services'}
    assert len(BLUEPRINT['services']) == 1
    assert SERVICE['type'] == 'web'
    assert SERVICE['name'] == 'recruitboard-api'
    assert SERVICE['plan'] == 'free'


def test_singapore_main_backend_and_pinned_python():
    assert SERVICE['region'] == 'singapore'
    assert SERVICE['branch'] == 'main'
    assert SERVICE['rootDir'] == 'backend'
    assert SERVICE['runtime'] == 'python'
    # Historical Render Blueprint keeps its original runtime; active hosting is now Vercel 3.12.
    assert ENV['PYTHON_VERSION']['value'] == '3.11.15'


def test_build_start_port_worker_and_health_are_exact():
    assert SERVICE['buildCommand'] == 'pip install -r requirements.txt'
    assert SERVICE['startCommand'] == 'uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1 --no-access-log'
    assert SERVICE['healthCheckPath'] == '/health'
    assert 'PORT' not in ENV  # Supplied by Render, never overridden.


def test_automatic_deploys_use_current_render_syntax():
    assert SERVICE['autoDeployTrigger'] == 'commit'
    assert 'autoDeploy' not in SERVICE  # Deprecated; avoid contradictory settings.


def test_all_backend_configuration_names_are_declared_once():
    tree = ast.parse((ROOT / 'backend/app/config.py').read_text())
    names = {
        node.args[0].value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == 'os'
        and node.func.attr == 'getenv'
        and node.args
        and isinstance(node.args[0], ast.Constant)
    }
    assert set(ENV) == names | {'PYTHON_VERSION'}
    assert len(SERVICE['envVars']) == len(ENV)
    assert 'SESSION_SECRET' not in ENV  # The application does not consume it.


@pytest.mark.parametrize('key', ['DATABASE_URL', 'ALLOWED_ORIGINS'])
def test_dashboard_only_values_have_no_committed_value(key):
    assert ENV[key] == {'key': key, 'sync': False}


def test_safe_production_and_shared_demo_defaults():
    expected = {
        'APP_ENV': 'production', 'COOKIE_SECURE': 'true',
        'DEMO_MODE': 'true', 'SEED_DEMO': 'true',
        'LOGIN_LIMIT': '10', 'WRITE_LIMIT': '120',
    }
    assert {key: ENV[key]['value'] for key in expected} == expected
    assert all(isinstance(entry.get('value', ''), str) for entry in ENV.values())


def test_official_render_schema_when_available():
    schema_path = ROOT / '.cache/render-docs/render.schema.json'
    if not schema_path.exists():
        pytest.skip('Official public schema is not cached; no network fetch in tests.')
    schema = json.loads(schema_path.read_text())
    validator = validator_for(schema)
    validator.check_schema(schema)
    validator(schema).validate(BLUEPRINT)