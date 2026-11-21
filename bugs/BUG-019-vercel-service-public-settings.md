# BUG-019 — Vercel Python service did not receive expected public defaults

Observed 21 November 2026 after the user added the private Production database variable and started a new deployment. The agent did not start a duplicate build. Deployment recruitboard-dp4hr49ec-divya-6411.vercel.app reached Ready in 48 seconds, and a names-only check confirmed DATABASE_URL was now present in Production.

The short /health check still returned HTTP 500 (2.05 seconds). Redacted startup logs now showed Config.validate failing at a different guard:

> RuntimeError: Production requires exact HTTPS allowed origins

Evidence: `bugs/20261121-162834-351333-vercel-corrected-production-smoke.txt` and `bugs/20261121-163055-vercel-corrective-runtime-redacted.txt`. The PostgreSQL/Secure-cookie format check was passed; an actual database connection was not yet verified. No secret value was read, printed, saved or pulled.

The top-level legacy env declaration had been relied upon to supply the approved public defaults to the Services backend. Runtime evidence shows those expected defaults were not available as intended. Schema validation alone did not prove delivery into the Python process. This is an implementation/deployment-configuration issue, not proof that the user's database credentials are wrong.

Fix: add an explicit Vercel ASGI entrypoint, vercel_entry:app, which calls a pure public-defaults helper before importing app.main. The helper supplies only APP_ENV, COOKIE_SECURE, DEMO_MODE, SEED_DEMO, ALLOWED_ORIGINS, LOGIN_LIMIT and WRITE_LIMIT. It never supplies, reads or overwrites DATABASE_URL or any session secret. Explicit operator overrides are preserved. Generic local/private app.main installations remain unchanged. Removed the misleading root env block and included all app/migration files in the wrapper's function bundle.

The user explicitly approved one additional corrective deployment after local testing. Local result: 109 backend checks passed, including four new public-default/override/idempotence/fresh-entrypoint tests; 8 configuration checks passed. The fresh-entrypoint integration uses isolated local SQLite, not production. No full live browser suite has been used. Cloud verification is pending the approved fix deployment; no success is claimed from local checks alone.

## Resolution verified

The approved wrapper deployment (691c5a5) advanced past the exact-origin configuration guard and revealed the separate pooled-Neon guard (BUG-020). After its transaction-lock correction, 556bbe8 passed public database health and all 66 live Chrome checks, including same-origin Secure/HttpOnly cookies, demo sign-in and all roles. Public-settings delivery is **resolved and live-verified**. The earlier root-env assumption/failure and every diagnostic are retained.
