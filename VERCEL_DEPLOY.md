# RecruitBoard — current Vercel-only deployment

The user explicitly approved this change on 21 November 2026. The previous Render/Netlify instructions and failed-deployment evidence remain historical. This deployment uses **Vercel Hobby for the website and API**, plus the user's existing **Neon Free PostgreSQL** database. Do not upgrade, enter payment information, create another account to evade quota, or change unrelated projects.

## Verified account and current state

- CLI identity: `divyapriyadharshini-git`.
- Approved workspace: **Divya**, slug **divya-6411**, plan **Hobby**.
- Created project: **recruitboard**.
- Public alias: **https://recruitboard-pi.vercel.app**. Latest deployment from 691c5a5 reached Ready, but the backend currently returns HTTP 500 because the saved Neon URL is pooled and the startup migration guard requires a direct connection. It is **not yet a working verified app**.
- No account block flag was reported. The CLI billing-usage query could not provide remaining quota, so availability is not guaranteed. Stop if the production deployment is refused by a Free-plan limit.
- DATABASE_URL is present in Production, confirmed by names-only metadata. After the prior public-settings fix exposed the pooled-connection guard, a new tested correction now supports **both pooled and direct Neon TLS URLs** by keeping the migration lock and initialization in one explicit transaction. **Do not change the existing private value for this correction.** Its cloud verification is pending deployment. No production database address is present locally, and no environment/secret pull command is permitted.

## One private dashboard step for the user

1. Open **https://vercel.com/divya-6411/recruitboard/settings/environment-variables**. Confirm the workspace/project names above.
2. Find the existing **DATABASE_URL** row, open its **⋯** menu, and choose **Edit**. Do not create a duplicate variable.
3. Name: **DATABASE_URL**.
4. Value: privately paste a valid Neon TLS connection string for project recruitboard, **production branch**. Both **pooled and direct** connections are supported by the corrected transaction-scoped migration lock. Keep `sslmode=require` and any provider-supplied channel-binding option. Do not manually edit the hostname. Existing users with a valid Production variable should leave it unchanged for this code correction.
5. Select **Production only**. Mark it **Secret/Sensitive** if the UI offers that choice. Do not select Development or download it.
6. Click **Save**. Do not click Deploy/Redeploy yet; the authorized CLI deployment will follow after confirmation.
7. Confirm that the Vercel website itself lists a row named **DATABASE_URL** tagged **Production** in this exact project. The chat confirmation button does not create the variable. Then tell the agent only **“The DATABASE_URL row is visible under Production.”** Never paste its value or an unredacted Environment screenshot into chat. A names-only preflight must confirm it before the separately authorized corrective deployment.

All other runtime values are non-secret and applied by backend/vercel_entry.py before app construction, using backend/app/deployment.py. Explicit dashboard overrides are preserved. Do not rely on a top-level vercel.json env block to deliver these values into the Services backend:

| Variable | Value |
|---|---|
| APP_ENV | production |
| COOKIE_SECURE | true |
| DEMO_MODE | true |
| SEED_DEMO | true |
| ALLOWED_ORIGINS | https://recruitboard-pi.vercel.app |
| LOGIN_LIMIT | 10 |
| WRITE_LIMIT | 120 |

No SESSION_SECRET is required or consumed: sessions use random opaque tokens and database digests. No SMTP or email credentials. Do not manually add PORT; Vercel invokes the ASGI app rather than running a user-facing Uvicorn port.

## Architecture and versions

Root vercel.json uses the documented **Services** model. Frontend root is frontend/, framework Vite, build `npm run build`, output dist. Backend root is backend/, framework FastAPI, entrypoint `vercel_entry:app`. `/api/*` and `/health` route to the backend without stripping the path; everything else routes to the frontend with its SPA fallback. Cookies remain same-origin; no Render/Netlify proxy is used.

Python is pinned to the supported **3.14 minor line**, verified locally on **3.14.6**. Vercel controls the actual patch version; an exact production patch is not claimed before observing the build. The attempted managed 3.12 download timed out and is retained as a diagnostic. Frontend uses Node **22.x**, with **22.22.0** pinned in its .nvmrc and local build dependency. Direct runtime dependencies are pinned in backend/requirements.txt and frontend/package-lock.json.

Backend region: **sin1 (Singapore)**; maximum function duration: **60 seconds**. Resumes remain in PostgreSQL, one PDF at most 1,048,576 bytes each; no persistent filesystem assumptions. Locked Alembic initialization runs once per process before API processing, whether or not the adapter calls lifespan. Seed uses actual database-generated IDs and refuses existing users/jobs/candidates/applications. SQL fixed-window rate limits share state across instances/restarts; hashed keys and expired-bucket cleanup avoid plaintext IP storage.

Initialization uses `engine.begin()` and `pg_advisory_xact_lock` on the same connection as Alembic and seeding, with a single outer commit and automatic rollback/release on failure. This works with transaction-mode pooling; there is no session-level lock or manual unlock. Timeout settings use `SET LOCAL` inside that transaction (15-second statement/10-second lock wait), not unsupported arbitrary startup options. psycopg auto-prepare is disabled for pooler compatibility. Future nontransactional/autocommit migrations must not be added without redesigning this locking contract.

## Safe deployment command — after private input is confirmed

From the isolated recruitboard repository, use the existing authenticated CLI; never pass an authentication token or database address in a command:

```sh
vercel deploy --prod --project recruitboard --scope divya-6411 --yes --archive=tgz
```

This is the one initially authorized production attempt. Do not use Pro/trial, `--turbo`, temporary deployments as a quota bypass, `vercel pull`, `vercel env pull`, or `vercel build` that downloads a cloud environment. Stop on a quota or billing restriction rather than changing accounts/plans. Only the project created above may be changed.

Before upload, `python tools/vercel_upload_audit.py` uses **--dry** to inspect selected filenames without deploying. .vercelignore excludes every .env*, CLI state, venv, node_modules, caches, browser profiles, local DBs, tests, reports and screenshots. If a CLI unexpectedly creates a credential file, do not open it; confirm it is ignored, remove it without reading, and tell the user.

No Vercel Git integration or automatic deployment connection is required for this CLI deployment. When pushing the migration to GitHub, use the documented **[skip render]** commit-message phrase to avoid triggering the old Render service; its Blueprint is unchanged and no Render resource is deleted. A reporting-only push must not be used to generate extra deployments.

## Verification and quotas

Only after deployment is Ready, make a short same-origin health/sign-in check. The expected /health response is HTTP 200 with `{"status":"ok"}`, from an actual PostgreSQL query. It must not be inferred from domain allocation or a static homepage.

Run the full live Chrome suite **once** at the canonical production domain after readiness. The script refuses another full live run through its exclusive marker. It discovers real IDs, labels TEST candidates, and cleans them via admin privacy actions. Preserve any failure and use only short targeted follow-up checks if approved; never delete the marker to rerun a full suite. No load tests or keep-alive loops.

Official docs checked directly on 21 November 2026:
- https://vercel.com/docs/services
- https://vercel.com/docs/services/config-reference
- https://vercel.com/docs/services/routing
- https://vercel.com/docs/services/pricing
- https://vercel.com/docs/functions/runtimes/python/python-version
- https://vercel.com/docs/plans/hobby
- https://vercel.com/docs/functions/limitations
- https://vercel.com/docs/limits/fair-use-guidelines

Current documented Free inclusions include first 100 GB Fast Data Transfer, first 10 GB Fast Origin Transfer, first 1,000,000 function invocations and first 1,000,000 service requests; account usage is shared across projects. Hobby supports 200 projects, 2 GB/1 vCPU functions and a maximum 300-second duration. Standard Python bundle limit is 500 MB; default request and nonstreamed response bodies are capped at 4.5 MB. RecruitBoard caps PDFs at 1 MB and does not enable paid large-body/performance features. When Hobby limits are exceeded, the docs generally require waiting for the applicable reset period (often 30 days). Do not infer remaining allowance from a zero price or absent block flag.

Remaining unverified items include actual Vercel cloud build/runtime, production PostgreSQL startup, same-origin routing/cookies in the deployed service, runtime client-IP semantics and remaining account quota. The earlier Render failure is not claimed fixed merely because hosting is changing.