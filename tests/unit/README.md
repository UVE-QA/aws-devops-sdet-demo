# tests/unit

Tests that need the application **in the same process**, so they can see things
no HTTP client can: what a log line looks like, and what happens when a handler
raises before any response exists.

Where a spec lives decides where it runs (the ADR-0025 rule, applied outside
Playwright). These run in `ci.yml` and locally, against imported code. They
NEVER run against a deployed environment — there is nothing to point them at.

```text
tests/unit/       imported code, no network, no database   ci + local
tests/api/        HTTP contract, destructive                stage + local
tests/db/         seed assertion, an ECS task in AWS        stage
tests/playwright/ browser; split smoke / regression         see ADR-0025
```
