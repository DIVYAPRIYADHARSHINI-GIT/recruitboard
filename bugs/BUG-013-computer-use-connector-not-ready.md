# BUG-013 — Computer Use connector setup is incomplete

Observed 21 November 2026, approximately 13:06 Asia/Kolkata. The user asked the agent to take browser access itself after the actual Render public service URL had not been supplied. The stated scope was limited to the existing recruitboard-api service overview in the user's intended Render account, copying its public URL and a brief health check. No Environment settings, secrets, resource changes, paid plans or Netlify access were included.

Tool called: enable_connector with connector_id native-computer.

Exact diagnostic: “Computer Use cannot be used yet: Install Codex and enable Computer Use in the ChatGPT desktop app, then reconnect. The user can fix this in Connectors.”

No computer/browser access was obtained. No Render account was inspected or changed, no secret was read or downloaded, and no live health request was made in this attempt. No screenshot could be captured because the connector was unavailable. This labelled transcript preserves the actual tool result.

Supported next step: the user completes Computer Use setup in Connectors and reconnects. Do not bypass this by reading local browser credentials, attaching to a private browser profile, asking for API keys or silently changing to another account-access workflow. Status: blocked pending connector setup or a user-supplied public URL/safe cropped overview screenshot.
