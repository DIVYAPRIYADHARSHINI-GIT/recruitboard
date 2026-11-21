# Approved public-documentation research

Checked 21 November 2026, Asia/Kolkata. User separately approved public documentation for Netlify, Render and Neon. These checks do not prove an account has unused quota. No dashboards, credentials, production connections or deployments were accessed during this research. Always confirm the dashboard's actual plan before creating a resource; stop if payment or an upgrade is required.

## Netlify

Official credit-plan and pricing pages report **300 credits/month** on the current Free plan, **15 credits per production deploy**, **20 credits/GB bandwidth**, and **2 credits per 10,000 web requests**. Older accounts may remain on legacy plans. Do not assume the quotas from an older tutorial apply to the user's account.

- https://docs.netlify.com/manage/accounts-and-billing/billing/billing-for-credit-based-plans/credit-based-pricing-plans/
- https://www.netlify.com/pricing/
- https://docs.netlify.com/build/configure-builds/manage-dependencies/
- https://docs.netlify.com/build/configure-builds/available-software-at-build-time/
- https://docs.netlify.com/manage/routing/redirects/rewrites-proxies

The build docs support Node selection through `.nvmrc`/`NODE_VERSION`; pinned **22.22.0**, also installed and checked locally. An initial broad search incorrectly claimed only Node 18 was supported; primary build docs corrected it (BUG-001). This is a static build, not a Netlify Function runtime.

External status-200 rewrites are documented. `frontend/scripts/netlify.mjs` generates `/api/* https://PUBLIC-BACKEND.onrender.com/api/:splat 200!` ahead of the SPA fallback. The public service URL is supplied via `API_PROXY_TARGET`, not a secret. Proxy requests have a documented approximately **26-second timeout**, shorter than a possible Render cold start. First visit can therefore require a retry after about a minute; no keep-alive ping or continuous polling is used to consume quota.

Host-only HttpOnly cookies and no-store API responses are chosen. Custom static response headers do not necessarily apply to proxied responses, so the backend itself sets its privacy/security headers. A successful local real-browser proxy test is evidence for the application flow, not proof of Netlify's deployed Set-Cookie behavior. Live browser verification remains required before claiming the hosting cookie issue is solved end to end.

## Render

Official docs report free web services sleep after **15 minutes** without inbound traffic and may take **about a minute** to wake. **750 free instance hours per workspace/month** are shared by free services. Build minutes and outbound bandwidth also have account-level quotas; inspect the dashboard before deployment. Files are ephemeral, persistent disks are unavailable on Free, services cannot scale horizontally, and restarts can occur.

- https://render.com/docs/free
- https://render.com/docs/python-version
- https://render.com/docs/deploy-fastapi
- https://render.com/docs/web-services
- https://render.com/docs/health-checks

Python can be selected with `PYTHON_VERSION`; pin **3.11.15**, which is the approved standalone local runtime used for verification. A Render build of this exact patch is not yet verified. Start command resolves the supplied `$PORT`, uses one worker, and disables access logging. Health path is **/health**, which executes `SELECT 1`. Do not use free Render PostgreSQL: it expires and is not part of this design.

## Neon

Official current pricing/FAQ pages report **100 projects**, **100 CU-hours per project/month**, **1 GB Postgres storage per project**, **5 GB public transfer per project/month**, **10 branches/project**, and an account-wide **20 GB storage cap**. Compute scales to zero after **5 minutes**; on Free this cannot be disabled. Free plan does not expire and requires no credit card. The October 2026 storage increase is documented; older 0.5-GB references are outdated.

- https://neon.com/pricing
- https://neon.com/faqs/free-plan-limits-and-quotas
- https://neon.com/blog/neon-free-plan-1-gb-per-project
- https://neon.com/docs/guides/sqlalchemy
- https://neon.com/docs/connect/choose-connection

Use a **direct** connection with `sslmode=require` for this one-worker service. Startup uses a session-level advisory lock, so transaction-mode pooled URLs are intentionally rejected. SQLAlchemy uses a small connection pool and pre-ping. A single direct URL can serve runtime and migrations; it is entered only by the user in Render and must never appear on the local machine, in GitHub, in this report or in chat. Forty 1-MB resumes alone could use about 40 MB; database rows, indexes and storage overhead also count against the quota.

## Remaining verification

Account-specific free plan, remaining quota, exact patch-runtime availability, production PostgreSQL migration compatibility, live proxy cookie handling, proxy cold-start behavior and deployed role journeys remain unverified until approved deployment actually occurs. No source linked here is a promise of future pricing.