# BUG-014 — Render deployment failed with exit status 1

Observed from the user's screenshot supplied on 21 November 2026 at approximately 14:42 Asia/Kolkata. Only relevant deployment details are transcribed here; the screenshot also contains unrelated workspace/account metadata and is not copied wholesale into the public repository.

## Visible evidence

- Service: recruitboard-api.
- Public URL: https://recruitboard-api.onrender.com.
- Badges: Python 3, Free, Blueprint managed.
- Repository: DIVYAPRIYADHARSHINI-GIT/recruitboard, branch main.
- Deployment commit: e8af870.
- Status: Failed.
- Deployment duration displayed: 1m 5s.
- Event text: “Exited with status 1 while running your code. Check your deploy logs for more information.”
- The UI labels the first deployment as starting November 21, 2026 at 12:33 PM and failing at 12:34 PM. No separate inference about the dashboard's timestamp zone is made.

## Interpretation and next step

The screenshot confirms a failed deployment; this is not merely an unverified claim that the service is sleeping. The Events summary does not identify the exception, failed startup step or environment issue. Do not infer a database failure, missing dependency or required paid upgrade from exit code 1 alone.

Next diagnostic: the user clicks the purple “deploy logs” link in the failed event and supplies the final startup/error lines, with any connection string, password or token redacted. No Environment screenshot is requested. Do not repeatedly redeploy, change secrets, upgrade, or make further health requests before diagnosis.

Status: OPEN — awaiting the actual deployment traceback/error. The two earlier bounded public health timeouts remain preserved separately. No secret was accessed and no new deployment or full live test suite was triggered by this diagnostic step.

## Additional screenshot evidence for final handoff

At the user's request, a cropped copy of their uploaded Events screenshot is retained as `BUG-014-render-deployment-failed-user-supplied-detail.png`, with provenance/crop metadata in the matching JSON file. It is user-supplied evidence, not a fresh agent dashboard capture. The crop omits unrelated workspace/account navigation and does not generate or edit the error text. The initial over-cropped derivative is retained separately and documented in BUG-015; it was not renamed or deleted. `BUG_REPORT.md` provides a concise shareable issue summary. This record's original failure description remains intact.
