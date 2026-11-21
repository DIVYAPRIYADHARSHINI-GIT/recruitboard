# BUG-020 — Pooled Neon URL blocks startup migrations

Observed 21 November 2026 at approximately 16:42–16:43 Asia/Kolkata. The separately approved public-settings fix (commit 691c5a5) was deployed once to Vercel Hobby. Build succeeded and public alias remained https://recruitboard-pi.vercel.app. Deployment: recruitboard-cn4x3g7j6-divya-6411.vercel.app.

The short /health check returned HTTP 500 after 2.13 seconds. A bounded, redacted runtime-log query confirmed the new vercel_entry.py wrapper was executing and the earlier public-origin guard was passed. Startup now fails with:

> RuntimeError: Use a direct Neon connection for startup migration advisory locking

Original evidence: `bugs/20261121-164225-628735-vercel-entrypoint-fix-live-smoke.txt` and `bugs/20261121-164301-vercel-wrapper-runtime-redacted.txt`.

The current production validation guard rejects a URL containing the Neon pooler-host marker. No connection string or password was viewed, downloaded, printed or saved; this diagnosis is based on the application's privacy-safe guard message and its reviewed source. Actual database connectivity/migrations remain unverified because startup stops before them.

Remediation: the user opens Neon → recruitboard → Connect → production branch and turns Connection pooling OFF. The user privately copies the newly displayed direct TLS connection string, edits the existing Production DATABASE_URL in the correct Vercel project, and saves it. Do not ask for the value in chat, remove TLS parameters, mutate the URL locally or bypass the migration guard. A new deployment requires explicit authorization; no further deployment or health request has been made in this step.

Status: OPEN pending private direct-URL correction and approved redeployment. The public-settings code fix is confirmed to have advanced startup beyond the previous guard, but the whole app is not yet verified working. Full live browser suite remains unused. No paid plan, other project changes, or secret pull is involved.

## Subsequent code remediation — approximately 16:54 Asia/Kolkata

The user asked to resolve the error without another private-value handoff. The agent verified official pooling/locking semantics and implemented support for the existing pooled URL instead: transaction-level advisory lock, all initialization on that same explicit transaction, one outer commit, rollback/release on failure, transaction-local timeout settings and disabled psycopg auto-prepare. This replaces the session-lock architecture; it does not merely bypass its guard. Secure cookies, exact origins and PostgreSQL-only production remain enforced. Six new regressions plus the full backend suite passed (115 total). The prior guidance requiring a direct URL is now superseded for the corrected code; the user need not change the secret. Cloud verification is pending and the original failure evidence remains intact.

## Resolution verified on Vercel — approximately 16:57–16:59 Asia/Kolkata

Committed/pushed source 556bbe8 and deployed it once to recruitboard-pd5tkvoml-divya-6411.vercel.app, aliased to https://recruitboard-pi.vercel.app. The canonical public /health returned HTTP 200 with {"status":"ok"} after a real PostgreSQL query in 0.81 s; session bootstrap returned 200 with demo enabled. The one full live Chrome suite then passed **66 checks, 0 failures**, including all three roles and 18 clean accessibility audits. Both live TEST candidates (41 and 42) were permanently deleted. No secret value was read or changed by the agent, and no paid upgrade was used. Status: **RESOLVED, verified live**. Original errors remain preserved.