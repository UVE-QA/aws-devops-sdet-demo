# ADR-0032: The 5xx signal is derived from the application's own JSON log

## Status
Accepted (Phase 16b).

## Context

Phase 16b asks for two things: structured logs with a request id, and a
CloudWatch metric filter on 5xx plus one alarm. They look like two tasks and
are one: the metric filter reads the log, so the shape of the log decides
whether the alarm can exist at all. A filter cannot compare `status` unless
`status` is a number at the top level of a JSON object, and it cannot name the
failing request unless the line carries an id.

There is also a cheaper signal already available and not used. The ALB
publishes `HTTPCode_Target_5XX_Count` for free, with no log parsing and no
custom metric. Choosing between them is the actual decision, and it is the
same shape as ADR-0026: two sources, and what matters is what each one can
observe.

```text
ALB metric              counts 5xx responses the target returned. Free, always
                        on, and blind to WHICH request, WHICH path, and why.
                        It also counts nothing when the ALB itself answers -
                        a 503 with no healthy target is ELB_5XX, not TARGET_5XX.

log-derived metric       counts lines the application wrote. Costs a custom
                        metric and depends on the app logging correctly. Names
                        the path, the request id and the duration, so the alarm
                        and the evidence are the same artifact.
```

The environment is created and destroyed every cycle (ADR-0017 D2a), which
constrains anything stateful attached to the alarm.

## Decision

### 1. One JSON object per line, on stdout, with `status` as a number

```json
{"ts":"2026-07-31T10:50:00.123Z","level":"info","msg":"request",
 "service":"aws-devops-sdet-demo","env":"stage",
 "request_id":"3f2a...","method":"GET","path":"/api/items",
 "status":200,"duration_ms":12.4}
```

`status` is an integer, not a string, because the filter pattern is
`{ $.status >= 500 }`. Quoting it would make every comparison a string
comparison and the alarm would silently never fire — a gate that cannot fail,
which this project has already been caught by once.

`path` is the route path, not the raw URL: query strings can carry values a
public log should not keep, and grouping by template is what makes the line
useful anyway.

### 2. Every line carries a request id, and the app both accepts and returns it

The app uses an inbound `X-Request-Id` when the caller sends one and generates
a UUID4 otherwise, holds it in a context variable so every line emitted during
that request carries it, and echoes it in the response header. A test, a
browser and a log line can therefore be joined by a value the test chose.

`X-Amzn-Trace-Id` is recorded ALONGSIDE it, never instead of it. It is the
only thing that ties a line to the ALB's own view of the same request, and it
does not exist locally, where most of the suite runs.

### 3. uvicorn's access log is turned off and the app writes its own

Two access lines per request, one JSON and one not, would leave the metric
filter reading half the traffic and a reader guessing which line is
authoritative. The application emits exactly one line per request, including
for requests that raise: the middleware catches, logs `status: 500`, and
re-raises. **The unhandled exception is the single most valuable 5xx there is;
a middleware that only logs successful responses cannot see it.**

Health checks are logged like everything else. The first thing wanted when a
health check starts failing is the health check's own line, and at one request
every 30 seconds against a 7-day retention the volume is not worth the
exception.

### 4. The alarm reads the log-derived metric, and says so

```text
namespace     aws-devops-sdet-demo/<env>     one per environment, no dimensions
metric        AppHttp5xx                     published only when a 5xx occurs
alarm         Sum >= 1 over one 60s period
```

The namespace carries the environment instead of a dimension because a
dimension value is a billable custom metric of its own and buys nothing here:
stage and prod never write to the same namespace.

This alarm reports **the application**, not the load balancer. An ALB that
answers 503 because no target is healthy produces no application log line and
will not raise it. That gap is accepted for v0 and named here so it is a known
limit rather than a false sense of coverage; `HTTPCode_ELB_5XX_Count` closes
it whenever the cost of a second alarm is worth paying.

### 5. `treat_missing_data = "notBreaching"`, deliberately

A metric filter publishes NOTHING when it matches nothing — not a zero. A
healthy environment therefore produces a metric with no data points at all,
and the default `missing` behaviour leaves the alarm in INSUFFICIENT_DATA for
its entire life. That state is indistinguishable from a misconfigured alarm on
sight, which is exactly the failure mode this project keeps finding. The alarm
reads OK when nothing has gone wrong, and it costs nothing until it does,
because the custom metric does not exist until the first 5xx is logged.

### 6. No notification action in this phase, and the reason is structural

An alarm notifies through SNS, and an SNS email subscription must be CONFIRMED
by clicking a link. The alarm lives in an environment that is destroyed every
cycle, so a topic beside it would be recreated every cycle: a confirmation
email every single time, and an alarm that notifies nobody in the window that
matters. A notification channel has to outlive the thing it reports on — the
fifth independent arrival at the ADR-0027 rule, and the first time it has been
reached from something other than state.

So the topic belongs at a permanent level, and creating a permanent level for
one topic is not what this phase is for. The alarm is created without an
action, its transition is verified against the AWS CLI, and the notification
is deferred with its price recorded here rather than being quietly skipped.

### 7. The break test uses a real fault, not an injected one

No fault endpoint is added. `/api/db-check` already returns **503** through its
real code path when PostgreSQL is unreachable, and 503 is a 5xx. Stopping the
database is a genuine failure that produces a genuine line, which is worth more
than a route that exists only to fail — and it means nothing that can break
production on purpose ships to production.

The two halves are joined by a LITERAL: the line the local fault actually
produces is the line put into the stage log group to prove the filter and the
alarm move. Not a line of the shape it was assumed to have.

## Consequences

- `app/src/logging_config.py` owns the formatter and the context variable; the
  middleware in `main.py` owns one line per request. Anything else that logs
  gets the request id for free.
- The ECS task definition gains an `environment` block — it had only `secrets`
  until now — to pass `APP_ENV`. That is a change to a SHARED module and goes
  to stage and prod in the same commit.
- The contract suite gains assertions on the header, in both directions, and a
  unit-level check that an unhandled exception still produces one line with
  `status: 500`. That check builds its own throwaway app; the fault route does
  not exist in `src.main`.
- Anything that greps the container log for plain text is now wrong. The demo
  script and the architecture document say what the line looks like.
