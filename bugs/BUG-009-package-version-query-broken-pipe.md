# Package version query diagnostic — broken pipe

21 November 2026, approximately 10:42 Asia/Kolkata. Read-only `pip index versions` output was piped into `head` to keep the result short. The registry returned FastAPI 0.165.0 and Uvicorn 0.54.0, but pip emitted `ERROR: Pipe to stdout was broken` and `BrokenPipeError: [Errno 32] Broken pipe` when head exited. The shell still returned 0 because the last pipeline component succeeded.

This was a command-output handling error, not a build or deployment failure. No credentials were involved. Retain this transcript and avoid truncating package-tool output with an early-closing pipe in future checks.
