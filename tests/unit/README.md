# tests/unit

Tests that need the code **in the same process**, so they can see things no HTTP
client can: what a log line looks like, what happens when a handler raises
before any response exists, and what the public launch endpoint does when its
control store fails.

Two subjects, two source roots — `app/` and `infra/self-service/src/`, both on
`PYTHONPATH` in `make test-unit`:

```text
test_access_log.py       the SHAPE of the JSON access line the 5xx alarm reads
                         (ADR-0032). A quoted status matches nothing, forever.
test_launch_refusals.py  the five refusals behind the public button (ADR-0035).
                         An endpoint refusing correctly and one refusing because
                         its store is broken look identical from outside, and
                         only one of them is a guardrail.
```

Where a spec lives decides where it runs (the ADR-0025 rule, applied outside
Playwright). These run in `ci.yml` and locally, against imported code. They
NEVER run against a deployed environment — there is nothing to point them at.

```text
tests/unit/       imported code, no network, no database   ci + local
tests/api/        HTTP contract, destructive                stage + local
tests/db/         seed assertion, an ECS task in AWS        stage
tests/playwright/ browser; split smoke / regression         see ADR-0025
```
