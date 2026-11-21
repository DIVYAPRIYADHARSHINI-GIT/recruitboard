# BUG-015 — Initial screenshot crop clipped the deployment label

During preparation of the user-requested report on 21 November 2026, the first privacy crop was visually reviewed in Designer. Its left edge cut off the beginning of the Render failed-event label and part of the error sentence. This was an evidence-preparation/layout mistake, not a new application or Render failure.

The initial derivative and its provenance JSON are retained unchanged as `BUG-014-render-deployment-failed-user-supplied.png` and `.json`. After reviewing the source image dimensions and visible event panel, the crop was corrected to include the entire Failed status and both event rows while excluding unrelated workspace/account navigation. The corrected image is a separate file, `BUG-014-render-deployment-failed-user-supplied-detail.png`; nothing was renamed, deleted or silently overwritten.

Both images derive from the user's actual screenshot. No error text or status was generated/edited, no account was accessed, and no network request was made. The corrected image, after visual verification, is the one to include in the report.