# RecruitBoard — architecture before implementation

Planned on 21 November 2026 (Asia/Kolkata). Original product, visual identity and implementation. All work stays in this repository. External service access requires separate explicit approval. This document is a design, not a claim of completion.

## 1. Repository and delivery stages

```
recruitboard/
  ARCHITECTURE.md
  README.md / DEPLOY.md / FINAL_REPORT.md / BUILDER_LOG.md
  frontend/              independent Vite + React + TypeScript project
    src/                 typed API client, components, routes, design tokens
    tests/               unit tests and Chrome journeys / accessibility
    public/              original static assets
    package.json / package-lock.json / .env.example
  backend/               independent FastAPI project
    app/                 database, models, schemas, security, services, routes
    migrations/          Alembic versioned schema
    tests/               isolated SQLite API and security tests
    requirements.txt / alembic.ini / .env.example
  screenshots/           actual browser captures only
  bugs/                  immutable numbered failure transcripts and captures
  evidence/              passing test summaries and deployment verification
```

Stages: (1) database, migration, security and seed; (2) full API and SQL reports; (3) responsive frontend and unit checks; (4) local Chrome journeys, accessibility, screenshots and corrections; (5) permission-gated publication and one final live suite; (6) final report and PDF if available. Run relevant tests at the end of each stage. Never erase or rename a failure record. Local suites may be repeated after fixes; no load testing or repeated full suites on free hosting.

## 2. Runtime architecture

Static React application calls relative `/api` URLs. Vite proxies locally. Planned Netlify external rewrite proxies `/api/*` to Render `/api/:splat`, subject to official documentation verification. The browser retains a single origin. Cookies are host-only (no Domain attribute), HttpOnly, Secure in deployed environments, SameSite=Lax, path `/`. No authentication tokens in localStorage. Exact allowed browser origins are checked on all unsafe requests, together with a synchronizer CSRF token bound to a database-backed session. The CSRF token is returned by the session endpoint and held in frontend memory; pre-authentication CSRF sessions protect sign-in too. No CORS wildcard and no cross-domain cookie fallback without explicit verification.

Backend: FastAPI, SQLAlchemy 2, Alembic; PostgreSQL in production and SQLite for development/tests. Dependencies and supported Node/Python versions will be pinned after documentation/toolchain verification. One Uvicorn worker, platform `$PORT`, access logs disabled. `/health` runs `SELECT 1`; no database URL or exception details are returned. Request errors must not echo submitted candidate records, passwords or tokens.

Automatic startup migration uses a PostgreSQL advisory lock (and a local SQLite file lock) around Alembic upgrade, making repeated starts safe. Seed only on explicit `SEED_DEMO=true` and an empty user table, within the same initialization lock. Production database address is entered by the user directly in Render; never copied locally. No permanent disk assumptions in production.

## 3. Database design

- **User**: id, name, normalized unique email, Argon2id password hash, role (`admin`, `recruiter`, `interviewer`), active, demo identity. No password hash in serialized responses.
- **Session**: digest of random session id, user id (nullable pre-auth), CSRF digest, expiry; raw secrets never persisted. Session rotation on authentication; invalidation on sign-out and role/account changes.
- **Job**: id, title, department, location, openings (positive integer), status (`open`, `on_hold`, `closed`), created timestamp.
- **Candidate**: id, name, normalized unique email, phone, source (`referral`, `job_portal`, `campus`, `website`), notes, created timestamp, anonymized flag. Tags in normalized CandidateTag rows with indexed tag values.
- **Resume**: candidate id as primary/foreign key, PDF binary and byte count, stored in the database. One PDF maximum, at most 1,048,576 bytes; MIME, `.pdf` extension and PDF signature required. Safe fixed filename on attachment download, `nosniff`, no-store. No original filename retained.
- **Stage**: stable key for reporting, editable label/order, active flag. Six required canonical stages cannot be removed; admin may relabel/reorder. This preserves funnel semantics while permitting configuration.
- **Application**: id, candidate id, job id, current stage key, created timestamp, optimistic version. Unique candidate+job; indexes on job+stage and candidate.
- **StageHistory**: application id, from/to stage, actor id, occurred timestamp, rejection reason id when relevant. Initial Applied event is recorded. Every actual transition adds history transactionally; repeats are no-ops. Concurrent moves must not silently overwrite each other.
- **RejectionReason**: id, label, active. Historical references preserved when deactivated.
- **Interview**: id, application id, interviewer id, starts_at UTC, mode (`video`, `phone`, `in_person`), created_by. Indexed interviewer+date and application.
- **Criterion**: stable key (`technical`, `communication`, `culture`), editable label and guidance. Required 1–5 ratings remain stable; not a diagnostic claim about a person.
- **Scorecard**: unique interview id, submitted_by, integer ratings 1–5, recommendation (`strong_yes`, `yes`, `neutral`, `no`, `strong_no`), feedback, submitted_at. Only assigned interviewer or authorized recruiting/admin actor may submit; interviewer cannot impersonate another interviewer or edit anyone else's card.
- **Offer**: unique application id, status (`draft`, `sent`, `accepted`, `declined`), optional fictional integer amount (minor units), updated_at. Controlled transitions; accepted offer does not silently move an application to Hired.
- **Activity**: candidate id, actor id, event type, privacy-safe event summary, timestamp. Notes stored on candidate; timeline events never duplicate free-text personal data.
- **Notification**: recipient id, application id nullable, event kind, generic message, read_at, created_at. Visibility is rechecked on read; old assignments cannot grant ongoing candidate access through notifications.

Foreign keys and cascading deletion cover candidate-owned data. Anonymization removes identifying fields, resume, tags, notes and scorecard feedback; replaces email with a unique non-contactable value; preserves non-identifying hiring statistics. Permanent deletion removes applications and their dependent records. Historical actor references survive user deactivation.

## 4. Server role policy (default deny)

Public: health and CSRF bootstrap; sign-in and demo sign-in require origin + pre-auth CSRF and rate limiting. Demo endpoint is unavailable unless demo mode is enabled.

All authenticated roles: own session, sign-out, own notifications. Recruiter/admin: jobs, candidate CRUD (excluding privacy erasure), all applications and moves, all interview scheduling, offers and reports. Admin only: user lifecycle and roles, stage/criterion/rejection settings, permanent candidate deletion or anonymization. Recruiter cannot create an admin or change their own role.

Interviewer: only candidates with an interview assigned to the current user; scoped list queries and object access use the SAME SQL assignment predicate. Candidate details expose only assigned applications/interviews and relevant scorecards, not other applications, offers, private notifications or recruiting activity. Candidate resume and notes obey the identical predicate. Job information is restricted to jobs of assigned interviews. No reports, global candidate counts, settings administration, offers, scheduling or stage moves. Scorecard writes require ownership of that specific interview, even if the user has another interview for the same candidate. Return 404 for non-visible object ids to avoid enumeration. Deactivated users lose access immediately.

## 5. Data flow and business rules

Create candidate → normalize email → unique constraint/409 duplicate warning → create application with Applied history in a transaction. Board and list share application data. Move menu and drag-and-drop call one endpoint with expected version; rejection opens an accessible confirmation dialog requiring an active reason; server enforces this regardless of UI. Forward/backward nonterminal moves are allowed; Hired/Rejected may be reopened explicitly via a recorded move. No stage history is fabricated or overwritten.

Schedule interview → validate active interviewer → transaction + timeline + in-app assignment notification. Submit scorecard → validate ratings/recommendation and assignment → unique scorecard + timeline + recruiter/admin notification. Stage change → history + timeline + relevant team notifications. No emails, telemetry or third-party analytics.

Candidate list search/filters/sort/pagination run server-side with bounded page sizes. Candidate permissions apply BEFORE filtering, pagination and counts. Resume upload is streamed up to the limit plus one byte and never written to disk. Writes and sign-in have bounded rate limiting; production single-worker limitation and process-reset behavior must be documented if in-memory counters are used.

## 6. Reports and definitions

SQL aggregation, not whole-table Python loops. Date range is inclusive start/exclusive next-day end, UTC. Funnel is an application-created cohort: count distinct applications that ever reached each stage, with stage conversions calculated against the preceding canonical stage; rejection shown separately. Skipped stages may make conversions non-monotonic; display this caveat. Also provide current-stage distribution. Time to hire is first Hired timestamp minus application creation for the cohort. Stage dwell uses ordered stage-history `lead()` and completed intervals; open intervals excluded and labelled. Source rates use cohort applications and distinct hired applications. Positions show current openings versus currently Hired applications, independently labelled as a snapshot. Offer acceptance is accepted/(accepted+declined), with sent/draft counts separately. Rejection reasons use rejection events in date range; activity groups history events by UTC day. Empty denominators return null rather than fabricated percentages.

CSV export uses server-side authorization and the same aggregates/date filters. Every text cell is escaped for CSV and prefixed with an apostrophe if its trimmed/leading-control-stripped content begins with `=`, `+`, `-`, or `@` or a dangerous control character.

## 7. Experience and design

Original calm editorial interface: deep ink, paper surfaces, restrained teal accent, original geometric RecruitBoard mark, accessible typography and clear status text. Light/dark tokens, semantic landmarks, visible focus rings, 44px primary touch controls, reduced-motion support. Responsive navigation and horizontally scrollable kanban with labelled columns and counts. Never drag-only: native keyboard-accessible Move to select/menu exists on every card. Pages: home, sign-in/demo role choices, jobs, board, filtered candidates, profile, interviews/scorecard, notifications, reports and admin. Accessible dialogs manage focus and Escape. Friendly loading/error/empty states; retry buttons where appropriate.

Persistent demo warning: fictional demo company; do not enter real candidate information into this shared demo. Explicit one PDF / 1 MB notice. Demo data: 6 users (1 admin, 2 recruiters, 3 interviewers), 5 jobs, ~40 candidates, 90-day histories, offers, interview assignments and scorecards. Demo identities cannot be converted into privileged permanent accounts silently. Random demo password hashes are not exposed; Try demo performs explicit demo-only server authentication. Real user passwords are supplied only in memory and hashed, never logged or committed.

## 8. Verification and evidence

Backend tests: role matrix and every interviewer read route, cross-interview scorecard denial, CSRF/session flags, input validation, history/concurrency, duplicate handling, PDF checks, notifications, rate limits, privacy erasure, SQL report fixtures and CSV injection. Frontend unit tests: API/error handling and pure formatting/report helpers. Chrome tests: full recruiter/interviewer/admin workflows, keyboard moves, rejection, offers/reports, unauthorized reads, mobile, themes and axe accessibility. Save real screenshots and immutable numbered bug diagnostics including failed tests/tool calls. Sanitization must prevent credential or candidate data leakage into evidence.

Live publication order after distinct approvals: GitHub public repository under DIVYAPRIYADHARSHINI-GIT, Neon database entered directly into Render by the user, Render health, Netlify frontend/proxy, exact backend origin configuration, one short live suite across roles. No payment information, no Vercel, no Render free PostgreSQL. Verify official free-tier/runtime/proxy documentation before relying on hosting; unknown limits remain marked unverified. All production test records explicitly deleted or listed. Final report distinguishes passed checks, historical failed attempts, open issues and unverified deployment.

## 9. User-approved hosting change — Vercel only, 21 November 2026

The user explicitly replaced the earlier no-Vercel instruction and approved preparing/deploying the frontend AND API on Vercel Hobby in workspace **Divya (divya-6411)**, account **divyapriyadharshini-git**, retaining the existing Neon database. One initial production attempt is authorized after compatibility checks and private dashboard entry of DATABASE_URL. No paid plan, new account to bypass limits, payment information, other project changes, credential-file inspection or secret download is allowed. CLI metadata confirms Hobby and no reported block flag; the billing usage command cannot provide remaining quota, so quota availability is not guaranteed. Stop on a quota/payment refusal. Existing Render failure evidence must remain intact.

Plan recorded before the Vercel implementation changes:

1. Use the officially documented **Services** configuration: frontend/ remains a Vite static service; backend/ remains a FastAPI Python service with entrypoint app.main:app. One public Vercel domain routes /api/* and /health to FastAPI, preserving paths; all other routes go to the frontend, with its SPA fallback. No Render/Netlify runtime dependency and no external cookie proxy. Keep host-only Secure HttpOnly SameSite=Lax cookies and exact-origin CSRF checks.
2. Vercel supports Python 3.12–3.14, not the original 3.11 pin. Select the supported 3.12 minor line (Vercel controls the patch); verify locally on managed Python 3.12.12 installed only inside this project. Keep pinned Node 22.22.0. Legacy Render instructions remain historical, not the active deployment path.
3. Make database initialization idempotent per application process and safe even if an ASGI adapter does not call lifespan. Use one local thread lock plus the existing PostgreSQL advisory lock, and run before processing API requests. Retain migration/seed behavior; expose only exception class/SQLSTATE in startup diagnostics, never raw errors or connection addresses. Bound PostgreSQL connection/statement waits and keep a small connection pool.
4. Replace process-local rate counters with an indexed SQL fixed-window counter shared across serverless instances. A new Alembic revision creates only the rate-limit table. Store a digest of the rate key, epoch window, expiry and bounded hit count; atomic upsert enforces the quota across workers/restarts, with expired buckets deleted. Existing role, CSRF, sessions, reports and resume rules stay unchanged. Add regressions for two limiter instances sharing one database, expiry and startup without lifespan.
5. Exclude all .env*, .vercel state, virtual environments, caches, local databases, reports, screenshots and tests from deployment uploads. Never use vercel pull, env pull or a local cloud build that downloads secrets. Create only the approved RecruitBoard project; set only public config values automatically. User enters the Neon DATABASE_URL privately in Vercel's dashboard.
6. Validate Vercel configuration against its public schema, run local backend/frontend regressions on the supported runtime, and then make the authorized production attempt. Keep the one full live browser suite unused until a healthy deployment exists. Do not push reporting-only changes that could waste builds; do not silently alter/delete the old Render service.

Primary documentation checked directly: https://vercel.com/docs/services, /docs/services/config-reference, /docs/services/routing, /docs/services/pricing, /docs/functions/runtimes/python/python-version, /docs/plans/hobby and /docs/functions/limitations. Current documented limits include 500 MB standard Python bundle, 4.5 MB default request/response body, Hobby 2 GB/1 vCPU and up to 300 s function duration. RecruitBoard's 1 MB PDF remains below the body limit. Account-specific remaining quota and the actual cloud deployment are still unverified at this planning point.

Implementation adjustment: the managed Python 3.12 download timed out. A standalone installed Python **3.14.6** is available and Vercel explicitly supports 3.14, so the active minor pin is **3.14** instead. A separate project-owned venv verified the updated compatible SQLAlchemy/Pydantic/psycopg pins. Initial serverless regressions passed 103 checks; sequence-offset seed regressions then found and corrected hardcoded seed IDs, bringing the final backend suite to 105. The seed now uses actual database-generated IDs and refuses existing business data. This is not proof of the earlier Render failure's root cause.

The approved Vercel project is `recruitboard` in `divya-6411`, with assigned domain `recruitboard-pi.vercel.app`. Seven non-secret runtime defaults are explicit in vercel.json after the public-variable API/CLI configuration attempt failed/stalled. DATABASE_URL is deliberately absent and is supplied privately by the user in the dashboard, Production only. Same-origin cookies need no additional SESSION_SECRET. The source upload is dry-audited, with environment/private data and report/test artifacts excluded. No production upload is authorized before the private input is confirmed.
