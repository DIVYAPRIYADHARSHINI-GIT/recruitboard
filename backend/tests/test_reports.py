from datetime import date, datetime, timedelta
import pytest
from sqlalchemy import delete
from sqlalchemy.orm import Session
from test_foundation import client, auth
from app.models import *
from app.reports import aggregates, safe_csv_cell


def fixture_cohort(db):
    db.execute(delete(Candidate))
    base = datetime(2026, 8, 1)
    for i, path in enumerate([['applied', 'screening', 'interview', 'offer', 'hired'], ['applied', 'screening', 'rejected'], ['applied']]):
        candidate = Candidate(name=f'TEST Report {i}', email=f'test.report.{i}@example.invalid', phone='', notes='', source='referral' if i < 2 else 'website', created_at=base)
        db.add(candidate)
        db.flush()
        app = Application(candidate_id=candidate.id, job_id=1, stage=path[-1], created_at=base)
        db.add(app)
        db.flush()
        for j, stage in enumerate(path):
            db.add(StageHistory(application_id=app.id, from_stage=path[j-1] if j else None, to_stage=stage, actor_id=2, occurred_at=base+timedelta(days=j*2), reason_id=1 if stage == 'rejected' else None))
        if i < 2:
            db.add(Offer(application_id=app.id, status='accepted' if i == 0 else 'declined', amount_minor=None))
    db.commit()


def test_exact_sql_funnel_time_to_hire_dwell_sources_positions_offers(client):
    with Session(client.app.state.engine) as db:
        fixture_cohort(db)
        result = aggregates(db, date(2026, 8, 1), date(2026, 8, 31))
    assert result['applications'] == 3
    assert [r['count'] for r in result['funnel']] == [3, 2, 1, 1, 1, 1]
    assert result['funnel'][1]['conversion'] == 66.7
    assert result['average_time_to_hire'] == 8.0
    assert all(x['days'] == 2 for x in result['stage_time'])
    assert next(x for x in result['sources'] if x['source'] == 'referral')['hire_rate'] == 50.0
    assert result['offers']['acceptance_rate'] == 50.0
    assert result['positions'][0]['filled'] == 1
    assert result['rejection_reasons'][0]['count'] == 1
    assert sum(x['changes'] for x in result['activity']) == 9


def test_report_empty_range_boundaries_and_csv(client):
    auth(client)
    with Session(client.app.state.engine) as db:
        fixture_cohort(db)
    result = client.get('/api/reports?start=2026-08-01&end=2026-08-01').json()
    assert result['applications'] == 3 and result['funnel'][1]['count'] == 0
    assert result['average_time_to_hire'] is None
    empty = client.get('/api/reports?start=2001-01-01&end=2001-01-02').json()
    assert empty['applications'] == 0 and empty['offers']['acceptance_rate'] is None
    assert client.get('/api/reports?start=2026-08-02&end=2026-08-01').status_code == 422
    assert client.get('/api/reports?start=2000-01-01&end=2026-08-01').status_code == 422
    export = client.get('/api/reports/export?start=2026-08-01&end=2026-08-31')
    assert export.status_code == 200 and 'attachment' in export.headers['content-disposition']
    assert 'Average time to hire (days),8.0' in export.text


@pytest.mark.parametrize('value', ['=1+1', '+SUM(A1)', '-1+4', '@evil', '  =HYPERLINK(1)', '\t=cmd', '\r=cmd', '\n=cmd', '\x00=1'])
def test_csv_formula_injection(value):
    assert safe_csv_cell(value).startswith("'")


def test_csv_injection_through_saved_job(client):
    auth(client)
    client.post('/api/jobs', json={'title': '=TEST_FORMULA()', 'department': 'TEST', 'location': 'TEST', 'openings': 1})
    assert "'=TEST_FORMULA()" in client.get('/api/reports/export').text