# BUG-018 — Vercel build Ready, runtime blocked by missing Production database configuration

Observed 21 November 2026, approximately 16:03–16:07 Asia/Kolkata. Workspace: Divya (divya-6411), project recruitboard, public alias https://recruitboard-pi.vercel.app. Source commit a86efa1. This is the first and only Vercel production attempt so far; it was explicitly approved after the user confirmed private DATABASE_URL entry.

## Actual results

The upload selected 44 source files (76.2 KB compressed). The build completed and Vercel reported Ready after approximately 50 seconds. The cloud log selected Python 3.14 from backend/.python-version. It also reported Node engine/bootstrap npm warnings; compilation itself succeeded. No Render/Netlify backend is used by this deployment.

The unauthenticated public GET /health returned HTTP 500 in 2.08 seconds. The full live browser suite was not started. The original diagnostic is `bugs/20261121-160444-117127-vercel-production-readiness.txt`.

A bounded query of at most 15 startup-log records was redacted before output/storage. It showed import of app/main.py reaching Config.validate(), then:

> RuntimeError: Production requires PostgreSQL and Secure cookies

The redacted traceback is `bugs/20261121-160606-vercel-runtime-redacted.txt`. No raw connection string, token, password or environment value was printed or saved.

A subsequent names-only Production environment lookup for this exact project reported DATABASE_URL **not listed**. APP_ENV was listed; other public defaults are supplied through vercel.json. Name/target evidence is in `evidence/20261121-160720-059883-vercel-production-variable-names.txt`.

## Cause and remediation status

The immediately verified blocker is missing DATABASE_URL in the project's Production environment. No conclusion is made about whether a value exists in another environment/project; none was inspected. The production safety guard is intentionally refusing a SQLite fallback or insecure configuration. It must not be bypassed by disabling Secure cookies or switching production to development mode.

The user must privately add the real direct Neon production-branch connection string as DATABASE_URL, targeted to Production, and save it. No example URI, shell/psql command or secret value should be pasted into chat. After confirmation, verify only the variable name/target before seeking/using approval for one corrective deployment; never pull the secret. The earlier user confirmation was trusted before the first upload; the improved preflight now checks non-secret presence/target metadata to avoid another unnecessary build.

Status: OPEN — awaiting private configuration correction and approval for a single corrective redeploy. No repeated full live suite, quota bypass, paid upgrade, other-project change, or secret download has occurred. This does not establish the root cause of the historical Render failure.

## Follow-up preflight — approximately 16:17 Asia/Kolkata

The user confirmed saving and explicitly approved a corrective deployment only after the name/target check passes. The new Production names-only lookup still reported `DATABASE_URL listed in Production: False`. It stopped the workflow before redeployment; **no corrective build/upload was made**. The original diagnostic is `bugs/20261121-161717-637061-vercel-database-name-preflight.txt`. CLI help confirms the non-JSON list command lists all project environment variables; the value-exposing --json option was not used. No conclusion is drawn about variables in a different project or environment.
