# RecruitBoard deployment — free plans only

> **Historical guide:** on 21 November 2026 the user explicitly replaced the no-Vercel instruction with a Vercel-only website/API deployment request. The active instructions are in [VERCEL_DEPLOY.md](VERCEL_DEPLOY.md). Do not create additional Render/Netlify resources for the new deployment. This guide and the Render failure evidence are retained, not erased.

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
4. Click **Create project**. Open **Connect** / **Connection details** for the **production** branch. The user has reported creating `recruitboard` on Free in AWS Asia Pacific 1 (Singapore); no agent database connection has been made.
5. Turn **Connection pooling OFF**. Copy the **direct** connection string privately. It must require TLS (`sslmode=require`; keep any provider-required channel-binding option).
6. Do not send the string to the agent and do not save it locally. Paste it only into Render's `DATABASE_URL` field in step 3.

The application converts `postgresql://` to `postgresql+psycopg://` internally. It intentionally rejects a `-pooler` hostname because startup uses a session-level advisory lock. One small direct SQLAlchemy pool is enough for this single-worker demo. The actual production database is created by Neon; schema creation/migration happens automatically inside Render on startup, not from the local machine.

## 3. Render backend — create from the root Blueprint

The user has separately approved Render dashboard guidance, required environment entries and one brief health check after sharing the real public service URL. The user creates the service in their intended Render account. No Render CLI or account-secret API is used. The root [render.yaml](render.yaml) defines exactly one **Free web service** and **no Render database**.

### Exact clicks

1. Open **[Render Dashboard](https://dashboard.render.com/) → New + → Blueprint** (not Web Service and not PostgreSQL).
2. Connect GitHub if needed, authorizing only **DIVYAPRIYADHARSHINI-GIT/recruitboard** where possible. In the repository list, click **Connect** beside that repository.
3. Enter Blueprint name **recruitboard**, select branch **main**, and leave **Blueprint Path** as **render.yaml** at the repository root. Do not use `backend/render.yaml`.
4. Review the proposed resources. It must show **one Free web service**, **recruitboard-api**, in **Singapore**, with **zero databases** and no paid resource. If Free/Singapore is unavailable or payment details are required, stop.
5. Enter **DATABASE_URL** and **ALLOWED_ORIGINS** in the initial Blueprint form when prompted; see the table below. Only the user enters the secret value, directly in Render.
6. Click **Deploy Blueprint** (some dashboard versions label the final confirmation **Apply**). Wait for the initial build/startup to finish; open the created **recruitboard-api** service from the Blueprint resources list.
7. Confirm its health path is **/health** and copy only the actual public **https://…onrender.com** service URL. Share that public URL and status, never environment values, so the approved brief health check can run.

**Existing-service warning:** if a manually created `recruitboard-api` already exists, do not assume a new Blueprint will automatically adopt it. The new-Blueprint/replication flow may propose a second independent service with a suffix. Stop if the plan shows a duplicate or unexpected resource; do not delete or modify the existing service to work around it. If this repository is already linked to a Blueprint, open that existing Blueprint instead of creating another. The agent has not inspected the user's Render account.

### Settings already supplied by render.yaml

| Setting | Exact value |
|---|---|
| Service | `recruitboard-api`, type `web` |
| Plan / region | `free` / `singapore` |
| Runtime / pinned Python | `python` / `3.11.15` |
| Branch / root directory | `main` / `backend` |
| Build command | `pip install -r requirements.txt` |
| Start command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1 --no-access-log` |
| Health check | `/health` |
| Automatic deploys | **On**: `autoDeployTrigger: commit` |

`autoDeployTrigger: commit` is Render's current documented equivalent of deprecated `autoDeploy: true`. This is enabled at the user's explicit request; subsequent eligible commits to the linked main branch can consume build quota. No preview environments, scheduled keep-alives, paid workers or databases are defined.

### Every backend environment variable

The two `sync: false` entries are prompted during **initial Blueprint creation**. Later Blueprint syncs leave their dashboard values alone. If updating an existing Blueprint instead, add any missing values manually in **service → Environment → Add Environment Variable**; Render does not prompt for new `sync: false` values during updates.

| Name | Value / handling |
|---|---|
| `PYTHON_VERSION` | Blueprint supplies `3.11.15` |
| `APP_ENV` | Blueprint supplies `production` |
| `DATABASE_URL` | **Prompted, `sync: false`. User privately pastes the Neon production-branch direct TLS URL. Connection pooling OFF; keep `sslmode=require` and provider-supplied channel-binding options.** |
| `COOKIE_SECURE` | Blueprint supplies `true` |
| `DEMO_MODE` | Blueprint supplies `true` for this explicitly shared fictional demo |
| `SEED_DEMO` | Blueprint supplies `true`; only an empty user table is seeded |
| `ALLOWED_ORIGINS` | **Prompted, `sync: false` (non-secret).** Enter the exact Netlify origin if known, otherwise `https://recruitboard-pending.invalid`. Replace the placeholder in Render's Environment settings after Netlify creation; no wildcard and no trailing slash. |
| `LOGIN_LIMIT` | Blueprint supplies `10` |
| `WRITE_LIMIT` | Blueprint supplies `120` |
| `PORT` | **Do not set**; Render supplies it |

**No SESSION_SECRET entry is needed or consumed.** The current backend generates random per-session tokens, stores only their digests in the database, and binds CSRF to each token. It does not use a signed client-side session payload or JWT requiring a shared signing key. Adding a dummy environment variable would not add security, so the Blueprint does not ask for an unused secret. No database address, token, password or session secret value is committed.

With the pending-origin placeholder, `/health` can work but frontend sign-in/writes are intentionally blocked until `ALLOWED_ORIGINS` is updated. A health success must be HTTP 200 with `{"status":"ok"}`; it runs a real DB query. The bare `/` path is not a frontend and may return 404. A previous check of a user-supplied placeholder hostname returned 404 and is retained as a diagnostic; it did not verify or disprove the real service/database.

Startup Alembic upgrade is protected by a PostgreSQL advisory lock; repeated starts are idempotent. Demo seed runs under the same initialization lock. No production DB address needs to be present locally. Resumes are binary database rows, not files on Render's ephemeral disk. No `neon init` or `neon deploy` commands are used.

Primary references, rechecked directly on 21 November 2026: [Blueprint YAML Reference](https://render.com/docs/blueprint-spec), [Blueprint setup and replication](https://render.com/docs/infrastructure-as-code), [public validation schema](https://render.com/schema/render.yaml.json).

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