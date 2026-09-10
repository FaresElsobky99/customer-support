---
name: test-verifier
description: >-
  Runs the non-integration backend test suite and reports pass/fail with a root-cause
  diagnosis. Use after backend changes to confirm nothing regressed. Does not modify code.
tools: Bash, Read, Grep, Glob
---

# Test verifier

Run the fast backend test suite and report the result. **Do not edit any files.**

## Steps

1. Run:

   ```bash
   uv run pytest tests/ -m "not integration" -q
   ```

2. If everything passes, report the pass count and stop.

3. If something fails, for each failing test:
   - Read the failing test function.
   - Read the source it exercises (follow the imports: route → service → repository).
   - Report: the test name, the exact failing assertion, and the most likely root cause.

4. Classify each failure as either:
   - **Environmental** — the DB is unreachable, the seed rows
     (`fares@example.com` / `ali@example.com`) are missing or changed, a token expired, or
     Gemini returned 429. These are not code regressions.
   - **Regression** — the code under test behaves differently than the assertion expects.

## Notes

- The suite (except `tests/test_agent.py`) is **not hermetic**: it connects to the real
  `DATABASE_URL` and some tests write rows. A connection error is environmental, not a bug.
- `tests/test_agent.py` is hermetic and should pass with no database at all — if it fails,
  that is always a real regression.
- Report findings concisely. The caller decides what to fix.
