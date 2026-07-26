# API contract tests

Black-box contract tests for the items slice. They speak HTTP to a RUNNING
application — the same container image that is deployed — rather than importing
FastAPI in-process. An in-process client would not exercise the image, the
network or a real PostgreSQL, so it could not serve as the gate against a
deployed stage environment, which is the whole point of running them here.

```text
BASE_URL   where to point them. Default http://localhost:8000 (docker compose).
           In Actions against stage this is the ALB URL.
```

DESTRUCTIVE: they create and delete rows. They run against stage, which is
seeded and disposable, and never against prod (ADR-0025). Every item they
create is registered for cleanup and removed at teardown, so the suite is safe
to run repeatedly against the same database.
