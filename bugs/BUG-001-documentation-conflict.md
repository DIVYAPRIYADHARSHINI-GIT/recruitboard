# BUG-001 — contradictory documentation-search summary

Found during pre-build hosting research, 21 November 2026. Tool: web_search; no screenshot applies.

Initial output: “The platform supports Node.js 18; it does not currently support Node.js 22”, citing a Netlify knowledge-base page. Follow-up query explicitly targeted official build-dependency documentation and returned that Node 22 is supported through `.nvmrc`/`NODE_VERSION`, with Node 24 the newer default.

Resolution: use the primary build docs https://docs.netlify.com/build/configure-builds/manage-dependencies/ and https://docs.netlify.com/build/configure-builds/available-software-at-build-time/ instead of the broad initial summary. Static build and Functions runtime are separate concerns. Pin a supported Node 22 patch for this static project. No live Netlify build has yet verified it.

This record is retained even after correction. No credential/account access occurred.
