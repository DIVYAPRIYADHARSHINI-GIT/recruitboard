# BUG-010 — vertically stacked search control

Found by visually reviewing the real desktop jobs screenshot in Designer on 21 November 2026. The search icon, input and hint were stacked vertically, making the search field unnecessarily tall and pushing the job cards down.

Cause: the shared label rule set `flex-direction: column`, while the search-field rule did not explicitly restore row layout. The same risk applied to compact sort and Move to labels. Fix: explicitly use row direction for `.search-field`, `.sort-control` and `.move-control`. Matching original screenshot: BUG-010-search-control-layout.png. Chrome regression and screenshot review follow the correction.
