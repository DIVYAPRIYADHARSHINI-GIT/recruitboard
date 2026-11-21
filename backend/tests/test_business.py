import secrets
from datetime import timedelta
import pytest
from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session
from test_foundation import client, auth
from app.models import *

PDF = b'%PDF-1.4\n1 0 obj<<>>endobj\n%%EOF'
SCORE = {'technical': 4, 'communication': 5, 'culture': 4, 'recommendation': 'yes', 'feedback': 'TEST assessment with specific fictional evidence.'}


def create(client, email='test.candidate@example.invalid'):
    response = client.post('/api/candidates', json={'name': 'TEST Candidate', 'email': email, 'job_id': 1, 'source': 'referral', 'tags': ['TEST'], 'notes': 'TEST fictional notes only'})
    assert response.status_code == 201
    return response.json()


def schedule(client, application, interviewer=4):
    response = client.post('/api/interviews', json={'application_id': application, 'interviewer_id': interviewer, 'starts_at': '2026-12-02T10:00:00+05:30', 'mode': 'video'})
    assert response.status_code == 201
    return response.json()


@pytest.mark.parametrize('method,path', [
    ('post', '/jobs'), ('put', '/jobs/1'), ('get', '/jobs/1/board'),
    ('post', '/candidates'), ('put', '/candidates/1'), ('put', '/candidates/1/resume'), ('delete', '/candidates/1/resume'),
    ('post', '/applications'), ('post', '/applications/1/stage'), ('get', '/applications/1/offer'), ('put', '/applications/1/offer'),
    ('get', '/interviewers'), ('post', '/interviews'), ('get', '/reports'), ('get', '/reports/export'),
    ('get', '/users'), ('post', '/users'), ('patch', '/users/1'), ('put', '/settings/stages/applied'),
    ('put', '/settings/criteria/technical'), ('post', '/settings/rejection-reasons'), ('put', '/settings/rejection-reasons/1'), ('post', '/candidates/1/privacy'),
])
def test_interviewer_cannot_use_recruiting_or_admin_endpoints(client, method, path):
    auth(client, 'interviewer')
    assert client.request(method, '/api'+path, json={}).status_code == 403


@pytest.mark.parametrize('method,path', [('get', '/users'), ('post', '/users'), ('patch', '/users/1'), ('put', '/settings/stages/applied'), ('put', '/settings/criteria/technical'), ('post', '/settings/rejection-reasons'), ('put', '/settings/rejection-reasons/1'), ('post', '/candidates/1/privacy')])
def test_recruiter_cannot_administer(client, method, path):
    auth(client)
    assert client.request(method, '/api'+path, json={}).status_code == 403


@pytest.mark.parametrize('role', ['admin', 'recruiter'])
def test_recruiting_journey_history_offer_and_notifications(client, role):
    user = auth(client, role)
    candidate = create(client)
    application = candidate['applications'][0]
    initial = client.get(f"/api/applications/{application['id']}/history").json()
    assert len(initial) == 1 and initial[0]['from_stage'] is None
    for stage in ['screening', 'interview', 'offer', 'hired']:
        response = client.post(f"/api/applications/{application['id']}/stage", json={'stage': stage, 'version': application['version']})
        assert response.status_code == 200
        application = response.json()
    history = client.get(f"/api/applications/{application['id']}/history").json()
    assert [x['to_stage'] for x in history] == ['applied', 'screening', 'interview', 'offer', 'hired']
    assert all(x['actor_id'] == user['id'] and x['occurred_at'] for x in history)
    assert client.post(f"/api/applications/{application['id']}/stage", json={'stage': 'screening', 'version': 1}).status_code == 409
    assert client.post(f"/api/applications/{application['id']}/stage", json={'stage': 'hired', 'version': application['version']}).status_code == 200
    assert len(client.get(f"/api/applications/{application['id']}/history").json()) == 5
    for status in ['draft', 'sent', 'accepted']:
        assert client.put(f"/api/applications/{application['id']}/offer", json={'status': status, 'amount_minor': 123400}).status_code == 200
    assert client.put(f"/api/applications/{application['id']}/offer", json={'status': 'draft', 'amount_minor': 123400}).status_code == 422
    assert any(n['kind'] == 'stage' for n in client.get('/api/notifications').json())


def test_rejection_requires_active_reason_and_can_reopen(client):
    auth(client)
    candidate = create(client)
    aid = candidate['applications'][0]['id']
    for reason in [None, 9999]:
        assert client.post(f'/api/applications/{aid}/stage', json={'stage': 'rejected', 'version': 1, 'reason_id': reason}).status_code == 422
    assert client.post(f'/api/applications/{aid}/stage', json={'stage': 'rejected', 'version': 1, 'reason_id': 1}).status_code == 200
    assert client.post(f'/api/applications/{aid}/stage', json={'stage': 'screening', 'version': 2}).status_code == 200
    history = client.get(f'/api/applications/{aid}/history').json()
    assert history[1]['reason_id'] == 1 and history[2]['from_stage'] == 'rejected'


def test_duplicate_email_is_case_insensitive_and_safe(client):
    auth(client)
    create(client)
    response = client.post('/api/candidates', json={'name': 'TEST Duplicate', 'email': ' TEST.CANDIDATE@example.invalid ', 'job_id': 1})
    assert response.status_code == 409 and 'already exists' in response.json()['detail']
    assert client.get('/api/candidates?q=TEST%20Candidate').json()['total'] == 1


def test_filters_pagination_sort_and_strict_inputs(client):
    auth(client)
    create(client)
    data = client.get('/api/candidates?tag=test&source=referral&stage=applied&job=1&sort=name&size=1').json()
    assert data['total'] == 1 and len(data['items']) == 1
    assert client.get('/api/candidates?page=0').status_code == 422
    assert client.get('/api/candidates?size=999').status_code == 422
    assert client.get('/api/candidates?sort=DROP%20TABLE').status_code == 422
    assert client.post('/api/jobs', json={'title': 'TEST', 'department': 'TEST', 'location': 'TEST', 'openings': True}).status_code == 422
    assert client.post('/api/candidates', json={'name': 'TEST', 'email': 'bad', 'job_id': 1, 'unexpected': 'ignored?'}).status_code == 422


@pytest.mark.parametrize('suffix', ['', '/resume'])
def test_interviewer_never_reads_unassigned_candidate(client, suffix):
    auth(client)
    candidate = create(client)
    client.put(f"/api/candidates/{candidate['id']}/resume", content=PDF, headers={'Content-Type': 'application/pdf', 'X-Filename': 'test.pdf'})
    auth(client, 'interviewer')
    assert client.get(f"/api/candidates/{candidate['id']}{suffix}").status_code == 404
    assert client.get('/api/candidates?q=TEST%20Candidate').json()['total'] == 0


def test_assignment_scopes_all_nested_paths_and_revocation(client):
    auth(client)
    candidate = create(client)
    aid = candidate['applications'][0]['id']
    assigned = schedule(client, aid)
    other = schedule(client, aid, 5)
    other_app = client.post('/api/applications', json={'candidate_id': candidate['id'], 'job_id': 2}).json()
    auth(client, 'interviewer')
    detail = client.get(f"/api/candidates/{candidate['id']}").json()
    assert [a['id'] for a in detail['applications']] == [aid]
    assert [i['id'] for i in detail['interviews']] == [assigned['id']]
    assert detail['offers'] == [] and detail['timeline'] == []
    for path in [f"/applications/{other_app['id']}", f"/applications/{other_app['id']}/history", f"/interviews/{other['id']}", f"/interviews/{other['id']}/scorecard"]:
        assert client.get('/api'+path).status_code == 404
    assert client.post(f"/api/interviews/{other['id']}/scorecard", json=SCORE).status_code == 404
    assert client.get('/api/candidates?interviewer=5').json()['total'] == 0
    with Session(client.app.state.engine) as db:
        db.execute(update(Interview).where(Interview.id == assigned['id']).values(interviewer_id=5))
        db.commit()
    assert client.get(f"/api/candidates/{candidate['id']}").status_code == 404
    assert not any(n['application_id'] == aid for n in client.get('/api/notifications').json())


def test_scorecard_validation_ownership_duplicate_and_notification(client):
    auth(client)
    candidate = create(client)
    interview = schedule(client, candidate['applications'][0]['id'])
    assert client.post(f"/api/interviews/{interview['id']}/scorecard", json=SCORE).status_code == 403
    auth(client, 'interviewer')
    assert any(n['kind'] == 'assignment' for n in client.get('/api/notifications').json())
    for value in [0, 6, '4', True]:
        assert client.post(f"/api/interviews/{interview['id']}/scorecard", json={**SCORE, 'technical': value}).status_code == 422
    assert client.post(f"/api/interviews/{interview['id']}/scorecard", json=SCORE).status_code == 201
    assert client.post(f"/api/interviews/{interview['id']}/scorecard", json=SCORE).status_code == 409
    auth(client)
    assert any(n['kind'] == 'scorecard' and n['application_id'] == interview['application_id'] for n in client.get('/api/notifications').json())


@pytest.mark.parametrize('content,mime,filename,status', [(PDF, 'application/pdf', 'cv.pdf', 200), (PDF, 'text/plain', 'cv.pdf', 415), (PDF, 'application/pdf', 'cv.exe', 415), (b'not a pdf', 'application/pdf', 'cv.pdf', 415), (b'%PDF-'+b'x'*1048572+b'%%EOF', 'application/pdf', 'cv.pdf', 413)])
def test_resume_type_extension_magic_and_limit(client, content, mime, filename, status):
    auth(client)
    candidate = create(client)
    response = client.put(f"/api/candidates/{candidate['id']}/resume", content=content, headers={'Content-Type': mime, 'X-Filename': filename})
    assert response.status_code == status


def test_resume_exact_limit_replacement_and_safe_download(client):
    auth(client)
    candidate = create(client)
    content = b'%PDF-' + b' '*(1048576-10) + b'%%EOF'
    path = f"/api/candidates/{candidate['id']}/resume"
    assert client.put(path, content=content, headers={'Content-Type': 'application/pdf', 'X-Filename': 'cv.pdf'}).status_code == 200
    assert client.put(path, content=PDF, headers={'Content-Type': 'application/pdf', 'X-Filename': '../../private.pdf'}).status_code == 200
    response = client.get(path)
    assert response.content == PDF and response.headers['content-disposition'] == 'attachment; filename="resume.pdf"'
    assert response.headers['x-content-type-options'] == 'nosniff' and 'no-store' in response.headers['cache-control']
    with Session(client.app.state.engine) as db:
        assert db.scalar(select(func.count()).select_from(Resume).where(Resume.candidate_id == candidate['id'])) == 1


def test_admin_anonymize_and_delete_cascade(client):
    auth(client, 'admin')
    candidate = create(client)
    cid, aid = candidate['id'], candidate['applications'][0]['id']
    interview = schedule(client, aid)
    client.put(f'/api/candidates/{cid}/resume', content=PDF, headers={'Content-Type': 'application/pdf', 'X-Filename': 'test.pdf'})
    auth(client, 'interviewer')
    client.post(f"/api/interviews/{interview['id']}/scorecard", json=SCORE)
    auth(client, 'admin')
    assert client.post(f'/api/candidates/{cid}/privacy', json={'action': 'anonymize', 'confirmation': 'CONFIRM'}).status_code == 200
    detail = client.get(f'/api/candidates/{cid}').json()
    assert detail['name'] == 'Anonymized candidate' and detail['notes'] == '' and detail['tags'] == [] and not detail['has_resume']
    assert detail['interviews'][0]['scorecard']['feedback'] == 'Removed for privacy'
    assert len(detail['history']) == 1
    assert client.post(f'/api/candidates/{cid}/privacy', json={'action': 'delete', 'confirmation': 'CONFIRM'}).status_code == 200
    assert client.get(f'/api/candidates/{cid}').status_code == 404
    with Session(client.app.state.engine) as db:
        assert db.get(Application, aid) is None
        assert db.get(Interview, interview['id']) is None
        assert not db.scalar(select(Notification.id).where(Notification.application_id == aid))


def test_admin_settings_users_and_session_revocation(client):
    auth(client, 'admin')
    password = secrets.token_urlsafe(24)
    response = client.post('/api/users', json={'name': 'TEST Account', 'email': 'test.account@example.invalid', 'password': password, 'role': 'interviewer'})
    assert response.status_code == 201 and 'password' not in response.text
    uid = response.json()['id']
    assert client.patch(f'/api/users/{uid}', json={'role': 'recruiter', 'active': False}).status_code == 200
    assert client.patch('/api/users/1', json={'role': 'interviewer', 'active': False}).status_code == 422
    assert client.put('/api/settings/stages/screening', json={'label': 'Initial review', 'position': 1}).status_code == 200
    assert client.put('/api/settings/criteria/technical', json={'label': 'Job skills', 'guidance': 'Give evidence.'}).status_code == 200
    reason = client.post('/api/settings/rejection-reasons', json={'label': 'TEST Reason'}).json()
    assert client.put(f"/api/settings/rejection-reasons/{reason['id']}", json={'label': 'TEST Reason', 'active': False}).status_code == 200


def test_notifications_are_private_and_writes_rate_limited(client):
    auth(client)
    own = client.get('/api/notifications').json()[0]
    assert client.post(f"/api/notifications/{own['id']}/read").status_code == 200
    auth(client, 'interviewer')
    assert client.post(f"/api/notifications/{own['id']}/read").status_code == 404
    client.app.state.config.write_limit = 2
    assert client.post('/api/notifications/999/read').status_code == 429


@pytest.mark.parametrize('path', ['/jobs', '/candidates', '/candidates/1', '/candidates/1/resume', '/applications/1', '/applications/1/history', '/interviews', '/interviews/1', '/interviews/1/scorecard', '/settings', '/users', '/notifications', '/reports', '/reports/export'])
def test_every_read_requires_sign_in(client, path):
    assert client.get('/api'+path).status_code == 401