# RecruitBoard deployment — free plans only

This file is a guide, not a claim of deployment. Current observed status and approved account actions are in `FINAL_REPORT.md` and `BUILDER_LOG.md`.

## Permission boundaries

Ask separately before accessing GitHub, Netlify, Render and Neon accounts/CLIs. Public documentation permission does not authorize account access. Explain the exact account and intended actions. Never enter payment details or upgrade. Stop if a Free plan is unavailable or exhausted. No Vercel, no Render PostgreSQL, no production secrets on the local machine. Never run commands that download hosting environment variables.

User enters secret values directly in hosting dashboards. Do not paste a Neon connection string, token or password into chat, a command, Git, a report or a screenshot. If a CLI unexpectedly creates `.env.local` or another credential file, do not read it; confirm ignore coverage, delete it without reading, and tell the user.

## 1. GitHub, after its explicit approval

Account: **DIVYAPRIYADHARSHINI-GIT**. Public repository name: **recruitboard**.

Work only inside the isolated repository. Confirm the authenticated username without printing tokens. Initialize `main`; set repository-local identity to `Divya Priyadharshini` and `divyapriyadharshini@softage.ai`. Never change global Git identity. Stage only project files, inspect staged filenames and sizes and scan text for secrets. No `.env*`, local database, venv, node_modules, browser profiles or generated credential files may be staged. Preserve all bug evidence. Public screenshots must contain fictional demo/TEST data only.

Create the public repository and push only after local verification and the staged-content audit pass. Do not enable automatic paid services or add production secrets to GitHub Actions. Avoid unnecessary commits/deploy triggers while preparing the free hosts.

## 2. Neon, after its separate explicit approval

The user chooses and confirms their Neon account. Use the **Free** plan. In the dashboard:

1. Click **New project** (or **Create a project**).
2. Project name: `recruitboard`; database name: `recruitboard` if the form offers it (otherwise retain the provided database name).
3. Choose an available Free region near the future Render service, and a supported PostgreSQL version. No paid add-ons, extra compute or payment details.
4. Click **Create project**. Open **Connect** / **Connection details** for the main branch.
5. Turn **Connection pooling OFF**. Copy the **direct** connection string privately. It must require TLS (`sslmode=require`; keep any provider-required channel-binding option).
6. Do not send the string to the agent and do not save it locally. Paste it only into Render's `DATABASE_URL` field in step 3.

The application converts `postgresql://` to `postgresql+psycopg://` internally. It intentionally rejects a `-pooler` hostname because startup uses a session-level advisory lock. One small direct SQLAlchemy pool is enough for this single-worker demo. The actual production database is created by Neon; schema creation/migration happens automatically inside Render on startup, not from the local machine.

## 3. Render backend, after separate Render approval and Neon/environment permission

The user chooses and confirms their Render account. Use the **Free web service**, not a database and not a paid worker. Dashboard steps:

1. **New + → Web Service → Build and deploy from a Git repository**.
2. Connect GitHub if needed; authorize only the new `DIVYAPRIYADHARSHINI-GIT/recruitboard` repository. Select it. Alternatively use its public repository URL if offered.
3. Name: `recruitboard-api` (an available unique name is fine); branch: `main`; root directory: **backend**.
4. Runtime: **Python 3**. Choose an available region near Neon.
5. Build command: **`pip install -r requirements.txt`**.
6. Start command: **`sh start.sh`**. This expands to `uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --workers 1 --no-access-log`.
7. Instance type: **Free**. Set **Health Check Path** to **`/health`** in Advanced/Health settings. Disable automatic deploys initially to avoid waste while preparing docs.
8. Under **Environment → Add Environment Variable**, enter the names below. The user enters the secret `DATABASE_URL` personally; the agent must not view it.

| Name | Value / handling |
|---|---|
| `PYTHON_VERSION` | `3.11.15` |
| `APP_ENV` | `production` |
| `DATABASE_URL` | **Secret: user pastes Neon direct TLS URL here only** |
| `COOKIE_SECURE` | `true` |
| `DEMO_MODE` | `true` for this explicitly shared fictional demo |
| `SEED_DEMO` | `true`; only an empty user table is seeded |
| `ALLOWED_ORIGINS` | Initially `https://recruitboard-pending.invalid` if Netlify URL is not allocated yet. Replace with the exact real Netlify origin in step 5; no wildcard and no trailing slash. |
| `LOGIN_LIMIT` | `10` |
| `WRITE_LIMIT` | `120` |
| `PORT` | **Do not set**; Render supplies it |

9. Click **Create Web Service / Deploy**. If any card/paid-plan requirement appears, stop. Do not work around a quota limit.
10. Wait for deployment to finish. Share only the public `https://…onrender.com` URL and redacted status/error text. Do not share environment screenshots or raw logs that contain a credential.
11. Make **one brief GET** to `https://PUBLIC-SERVICE.onrender.com/health`. Expected: HTTP 200, `{"status":"ok"}`. The endpoint executes a real DB query. A 503 means database readiness is not proven. Stop and diagnose; never claim success just because a web page loads.

`render.yaml` is a reference blueprint, not permission to apply it. Automatic startup Alembic upgrade is protected by a PostgreSQL advisory lock; repeated starts are idempotent. Demo seed runs under the same initialization lock. No production DB address needs to be present locally. Resumes are binary database rows, not files on Render's ephemeral disk.

## 4. Netlify static frontend, after separate Netlify approval

The user chooses and confirms the Netlify account/team and that its actual plan is Free with available quota. Do not access another team or enable paid features.

1. **Add new project / Add new site → Import an existing project → GitHub**.
2. Select only `DIVYAPRIYADHARSHINI-GIT/recruitboard`, branch **main**.
3. Base directory: **frontend**. Build command: **`npm run build && node scripts/netlify.mjs`**. Publish directory: **dist** relative to the base. The root `netlify.toml` contains these settings.
4. Under **Environment variables**, add the following non-secret values (requires the user's prior environment-variable permission):

| Name | Value |
|---|---|
| `NODE_VERSION` | `22.22.0` (also pinned in `.nvmrc` and TOML) |
| `VITE_API_BASE` | `/api` |
| `API_PROXY_TARGET` | The public Render **origin only**, e.g. `https://PUBLIC-SERVICE.onrender.com`; **never** a database URL or token |

5. Use an available project/site name such as `recruitboard`. Click **Deploy** once. Stop if a plan limit blocks deployment. No functions, scheduled pings, analytics add-ons or payments are needed.
6. Record the allocated public `https://…netlify.app` origin. Do not assume the preferred name was available.

The build script validates the public Render origin and generates `_redirects` with the external `/api/*` proxy **before** the SPA fallback. Netlify officially supports external status-200 rewrites. Static security headers are in TOML; backend API responses set their own `Cache-Control: no-store, private` because proxy response-header handling differs from static assets.

## 5. Exact-origin update and one final live suite

With Neon/environment and Render permissions already granted, the **user** opens Render → `recruitboard-api` → **Environment**, edits **`ALLOWED_ORIGINS`** to the exact Netlify origin, saves and redeploys/restarts the backend once. No wildcard, no localhost in production. Keep `COOKIE_SECURE=true` and host-only cookies (no Domain attribute). `SameSite=Lax` is correct because the browser calls its own `/api` origin through the proxy. Do not silently switch to third-party cookies.

First allow Render to wake. Free services sleep after **15 minutes of inactivity** and can take **about a minute** to wake. Netlify's roughly 26-second proxy timeout can expire first. A first attempt may show a retry state; wait and retry briefly rather than running continuous pings or load tests. Neon may also have scaled compute to zero.

Run the full live browser suite **once only**, after configuration is ready and with explicit live-test approval:

```sh
cd frontend
mkdir -p ../.browser/tmp
# URL below is public, not a credential. Use the actual approved Netlify URL.
TEST_BASE_URL=https://PUBLIC-SITE.netlify.app ALLOW_LIVE_ONCE=yes \
TMPDIR="$PWD/../.browser/tmp" node tests/browser.mjs
```

The script refuses nonlocal execution without the approval flag and creates an exclusive `evidence/live-suite-started.json` marker. Never delete the marker to repeat the full live suite. If a live failure occurs, retain screenshots/transcripts and limit further checks to a short targeted smoke test approved by the user.

Verify all three demo roles, HttpOnly/Secure cookie attributes, no auth cookie visible to JavaScript, sign-in surviving reload, candidate creation, keyboard and drag moves, rejection reason, assignment/scorecard, offers/reports, downloads, exact-origin behavior and no unexpected browser console/CORS errors. Save actual live screenshots. Test candidates are labelled TEST and deleted through the admin API/UI; the evidence lists their IDs and cleanup status. No untracked production test records are acceptable. If any record cannot be removed, explicitly list it in `FINAL_REPORT.md`.

## Current documented Free-plan limits

Checked from official documentation on 21 November 2026; source URLs and research caveats are in `evidence/HOSTING_RESEARCH.md`. Check the actual account dashboard before spending quota.

- **Netlify:** current credit plan 300 credits/month; production deploy 15 credits; bandwidth 20 credits/GB; requests 2 credits/10,000. Legacy account plans may differ. Proxy timeout around 26 seconds. Do not enable auto-recharge/paid usage; stop at a limit.
- **Render:** 750 free instance hours/workspace/month; sleeps after 15 minutes, about one-minute wake; ephemeral disk, no persistent free disk and no scaling. Build/outbound quotas also apply and must be checked for the account. Do not use its expiring free PostgreSQL.
- **Neon:** current Free docs show 100 projects, 100 CU-hours/project/month, 1 GB storage/project, 5 GB public transfer/project/month, 10 branches/project, 20 GB total account storage cap. Five-minute scale-to-zero on Free. No credit card/no fixed expiry. Binary resumes and indexes count toward storage.

## Secrets, rollback and operational honesty

Do not put tokens, passwords or connection strings in GitHub, frontend code, `.env` files on the local machine, CLI arguments, screenshots or reports. Host secrets stay in the provider dashboard. All `.env*` files are ignored, including example templates; README documents the same variables and provides a placeholder-template generator for clones.

For a failed deployment, capture a redacted diagnostic and its actual error. Do not upgrade a plan to fix it. Prefer reverting the Git commit/redeploying a known working application; schema downgrades can destroy data and require explicit approval/backups. Free-host backup/restore and real PostgreSQL disaster recovery are not verified by SQLite tests. No availability or compliance guarantee is claimed.