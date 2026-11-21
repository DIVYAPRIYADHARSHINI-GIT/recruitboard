# RecruitBoard

**Make room for great people.**

An independently designed hiring workspace: a job-specific kanban, candidate profiles, assigned interviews, structured scorecards and SQL-powered hiring reports. Original identity and application code; no real product's branding or code copied. The sample company **Crescent Labs** and every seeded person are fictional.

> **Shared demo: do not enter real candidate information.** Demo admins can anonymize or permanently delete records. The demo is not an appropriate place for confidential hiring data.

## Two projects, one repository

- `frontend/`: Vite, React, TypeScript, static output in `dist/`. Pinned Node **22.22.0**. System fonts, Lucide generic UI icons and an original RecruitBoard mark. No email, analytics or external image/font requests.
- `backend/`: FastAPI, SQLAlchemy 2, Alembic, Argon2id, SQLite locally, PostgreSQL on Neon for the intended deployment. Pinned Python **3.11.15**. All direct Python dependencies in `requirements.txt`.
- `ARCHITECTURE.md`: design written before implementation, including data model, server policy, reports and data flow.
- `BUILDER_LOG.md`, `bugs/`, `evidence/`, `screenshots/`: observed build history, retained failures, real test outputs and real browser captures.
- `DEPLOY.md`: permission-gated GitHub → Neon → Render → Netlify instructions. **No Vercel. No expiring Render PostgreSQL.**

Live deployment status and links are recorded in `FINAL_REPORT.md`; do not infer deployment from the presence of configuration files.

## Roles

| Capability | Recruiter | Interviewer | Admin |
|---|---|---|---|
| Jobs, all candidates, applications and moves | Yes | No | Yes |
| Assigned candidate details, resume and shared notes | Yes | Assigned interviews only | Yes |
| Interview scheduling and offers | Yes | No | Yes |
| Submit an interview scorecard | No | Only their exact assigned interview | No |
| Read submitted scorecards | All | Own assigned interviews only | All |
| Reports and CSV export | Yes | No | Yes |
| User roles, stages, criteria and rejection reasons | No | No | Yes |
| Candidate anonymization/permanent deletion | No | No | Yes |

The scorecard-submission rule deliberately prevents recruiters/admins from impersonating an interviewer. Admin includes all recruiter capabilities, plus administration. Every endpoint is checked on the server. Lists, counts, profiles, resumes, nested applications, histories, interviews and notifications all enforce assignment scope. Hidden/nonexistent candidate IDs return 404 to interviewers.

## Demo identities

Use **Try demo recruiter**, **Try demo interviewer**, or **Try demo admin** on the sign-in page. The public demo endpoint is enabled only with `DEMO_MODE=true`; it is not a production sign-in bypass.

| Demo display name | Identity | Role |
|---|---|---|
| Demo Admin | `admin@recruitboard.example` | admin |
| Demo Recruiter | `recruiter@recruitboard.example` | recruiter |
| Demo Recruiter Two | `recruiter.two@recruitboard.example` | recruiter |
| Demo Interviewer | `interviewer@recruitboard.example` | interviewer |
| Demo Interviewer Two | `interviewer.two@recruitboard.example` | interviewer |
| Demo Interviewer Three | `interviewer.three@recruitboard.example` | interviewer |

The three buttons use the first identity of each role. There is **no shared demo password to publish**: seed hashes an unexposed random value, and demo identities cannot use the ordinary password endpoint. Real user passwords are supplied in memory and hashed with Argon2id. Never reuse a real password in the shared demo. Demo identities cannot be deactivated or reassigned by other demo visitors.

The idempotent seed creates six users, five jobs and forty fictional candidates across the six canonical stages, with histories over the past 90 days, assigned interviews, feedback, offers, rejections and in-app notifications. Startup seeds only if explicitly enabled and the user table is empty. Rerunning never overwrites an existing workspace.

## Local run

Use a standalone Python 3.11.15 installation. All commands below are run inside this repository; they do not require a production database, hosting CLI or any secret.

```sh
cd backend
python3.11 -m venv .venv
.venv/bin/python -m pip install --cache-dir ../.cache/pip -r requirements.txt
APP_ENV=development COOKIE_SECURE=false DEMO_MODE=true SEED_DEMO=true \
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:4173,http://127.0.0.1:4173 \
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1 --no-access-log
```

In another terminal, from the repository:

```sh
cd frontend
# Select Node 22.22.0 using your installed version manager (.nvmrc is provided).
npm ci --cache ../.cache/npm --userconfig /dev/null --no-audit --no-fund
npm run dev
```

Open `http://localhost:5173`. For the tested static build: `npm run build`, then `npm run preview` and open `http://127.0.0.1:4173`. Vite proxies `/api` to the loopback backend; cookies stay on the frontend origin. `GET http://127.0.0.1:8000/health` executes a real database query.

The SQLite file defaults to `backend/recruitboard.db` and is ignored. Resumes are in the database, not on disk. **One PDF, maximum 1 MB (1,048,576 bytes) per candidate**. Upload checks MIME, `.pdf` extension, PDF signature/end marker and streamed byte count. Download is an attachment with a fixed filename, no-store and nosniff headers. This is not a malware-scanning service; do not upload untrusted real documents to the demo.

### Environment documentation

All `.env*` files, **including the local `.env.example` templates**, are ignored to honor the no-environment-files publication rule. Templates are provided locally; after cloning, `python3 tools/create_env_examples.py` recreates missing `.env.example` templates containing placeholders only. The app does not automatically read dotenv files; export variables in your shell locally, or use the hosting dashboard in production. Never put database credentials in Vite variables.

Backend variables: `DATABASE_URL` (SQLite default locally; secret Neon direct URL only in Render), `APP_ENV`, `ALLOWED_ORIGINS`, `COOKIE_SECURE`, `DEMO_MODE`, `SEED_DEMO`, `LOGIN_LIMIT`, `WRITE_LIMIT`. Frontend: `VITE_API_BASE=/api`; Netlify build only: public `API_PROXY_TARGET`.

## Working with the pipeline

Add a candidate to an open job. Emails are normalized and unique; duplicates produce a 409 warning instead of another profile. Additional applications may be created for other open jobs. Search and filter by job, stage, source, tag and interviewer; sort and paginate on the server.

Each actual stage move records actor, timestamp, source/destination and rejection reason if applicable. Initial Applied is also recorded. Drag-and-drop and the native keyboard/touch **Move to** control use the same endpoint. A rejection requires a confirmation and active reason. Moving a stale version returns 409 instead of silently overwriting a teammate's move. Stages may be skipped or reopened, with history retained.

Schedule an interview from a profile; the assigned interviewer sees an in-app notification. They can read the candidate's notes/resume and submit 1–5 ratings for technical skills, communication and culture fit, an overall recommendation and written feedback. One immutable scorecard per interview. Recruiters/admins receive a notification. Offers progress draft → sent → accepted/declined; no emails are sent and acceptance does not silently mark Hired.

Admins may relabel/reorder the six stable stages, customize the three required criteria, deactivate/add rejection reasons, create/deactivate users and change roles. Deactivation/role change revokes sessions. Self-deactivation/demotion and changes to protected demo identities are blocked. Privacy actions require typing CONFIRM. Anonymization removes identifying fields, tags, notes, resumes and scorecard feedback while preserving non-identifying hiring metrics; permanent deletion cascades candidate-owned records.

## Report definitions

Date boundaries are UTC; start and end dates are inclusive. Maximum 366-day range. The funnel is a cohort of applications created in range, counting distinct applications that reached each stage by range end. Conversions divide by the previous canonical stage; skipped/reopened stages can make these non-monotonic. First-Hired minus creation is time to hire. Stage duration averages completed intervals; ongoing intervals are excluded.

Source rates count applications, not deduplicated people across jobs. Current-stage counts, job openings/filled counts and offer statuses are present-day snapshots, labelled in the UI. Offer acceptance is accepted/(accepted+declined), not accepted/all drafts. Rejection reasons and activity use event dates. No data returns a dash rather than a fabricated percentage. SQL grouping/window functions perform calculations; CSV exports use the same aggregates and neutralize formula-leading text, including whitespace/control-character prefixes.

## Verification

```sh
mkdir -p .test-data
cd backend
.venv/bin/python ../tools/check.py backend .venv/bin/python -m pytest -q --basetemp=../.test-data/manual
cd ../frontend
npm test
npm run build
# With the backend and production preview running:
mkdir -p ../.browser/tmp
TMPDIR="$PWD/../.browser/tmp" node tests/browser.mjs
```

Chrome test executable defaults to the installed macOS Google Chrome path. Browser profiles, downloads and screenshots stay in this repository. Tests save failures without deleting or renaming them, label TEST candidates and clean them using admin privacy deletion even when a journey fails. Backend tests use isolated disposable SQLite databases, never production. A live browser run is permission-gated by `TEST_BASE_URL` and `ALLOW_LIVE_ONCE=yes`, with an exclusive one-run marker; do not bypass/delete that marker or repeat the full live suite. No load tests.

See `FINAL_REPORT.md` for actual latest counts, historical failures and outstanding verification; tests existing in source are not evidence they passed.

## Operational limits

- Single-worker in-memory rate limiting resets on restart and is not a distributed abuse-control system. Sign-in default: 10 attempts/15 minutes per connecting IP; writes: 120/minute. Forwarded client-IP accuracy behind Netlify/Render still needs live verification; a shared proxy IP can share limits.
- Host-only HttpOnly Secure SameSite=Lax cookies in production; synchronizer CSRF and exact Origin checks on writes. Local HTTP explicitly uses non-Secure cookies. No tokens in localStorage. There is no password-reset email, MFA or SSO.
- PDF type checks do not replace antivirus/CDR. Notes and feedback are plain text, not HTML. No field-level encryption beyond the database provider's capabilities is claimed.
- Board displays latest 500 cards, with real column counts and a notice; use the paginated candidate list for larger jobs. Candidate timeline shows latest 200 generic activities. Notifications show latest 100. Interview list filters apply to the current 30-item page. User admin list caps at 500.
- Stage additions/removals and arbitrary scorecard fields are intentionally not supported: stable keys preserve reporting. Current positions may be overfilled; the app does not enforce opening capacity as a hard hiring rule.
- Free hosting sleeps and has quotas. This is a functional demo, not an enterprise ATS or compliance certification. No SLA, legal retention policy or production disaster-recovery claim.

## Private bootstrap

For a separate approved private installation with an empty database and demo flags disabled, `python -m app.bootstrap_admin` creates the first admin interactively with hidden password prompts. Run it on the approved host with its database environment already configured; never pull that environment locally. Render Free may not offer a shell for this operation; do not upgrade or work around platform permissions. The shared seeded demo does not need this command.