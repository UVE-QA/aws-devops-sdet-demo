# Session 2026-07-26 — Phase 10: the thin application slice

- Phase: 10 (M2). **Code complete, NOT closed** — the phase's closing criterion
  requires a run against deployed stage, which is billable and was deliberately
  deferred to the next session.
- Request: run Phase 10 as planned in `docs/next-phases.md`, steps 1–4 plus
  local validation, with the paid `deploy-stage → destroy` cycle held back.
- Tooling: Cowork chat driving from a fresh clone of `origin/main`, authoring
  commits and delivering them as one `git format-patch` mbox. Execution and
  validation on the devbox.
- **No AWS API was called and nothing was applied. Zero cost.**

## Result

```text
5 commits   7f94388  the items slice: create, list, delete, with real negatives
            9a9068e  the static page drives the items API
            87d09b4  read-only and destructive split by directory (ADR-0025);
                     the UI-write assertion
            9c166df  workflows: each suite where it belongs; one shared
                     ecs-run-task helper
            <this>   session close: cursor, plan, log, summary, index
```

`demo_items` gains a nullable `description` in revision 0002 — the first time
the migration chain is longer than one revision, so `alembic upgrade head`
against an existing database is finally exercised as a distinct code path from
creating the schema from nothing.

Test coverage goes from "one smoke test and a seed assertion" to:

```text
19  HTTP contract cases (pytest + httpx), most of them negative
 2  read-only Playwright specs   project "smoke"      — runs everywhere
 3  destructive Playwright specs project "regression" — never prod
 1  database assertion after a UI action
 1  guard that no spec escapes its project
```

## The finding — a guarantee that was a comment

`promote-prod.yml` had a step named "Read-only smoke against prod" whose comment
explained, correctly, that destructive tests belong to stage. It then ran
`npx playwright test`, which executes the entire `testDir`.

The comment described an intention the command had no way to honour. It held
only because no destructive spec existed. The first one — added by this phase —
would have made prod destructive silently: nothing would have gone red, no step
would have changed name, and the comment would have gone on reading as a
guarantee. The first symptom would have been rows appearing and disappearing in
the environment an interviewer is pointed at.

This is the project's documented failure mode once more: **"it looked finished",
not "it broke"**. It was found by reading the workflow before writing the spec
that would have broken it, which is the only detector this class has.

ADR-0025 records the fix: the suites are separated by DIRECTORY, bound to
Playwright projects, and every caller names its projects explicitly. stage names
both rather than omitting the flag, because "run everything" is precisely how
prod nearly inherited the destructive suite.

## The guard, and why it was broken on purpose

A directory convention that nothing enforces is a comment with a longer name. A
spec placed outside both directories matches neither project, so Playwright runs
it in no project and reports nothing about it: green everywhere, test absent.

Same shape as a `make tf-validate` that discovers zero root levels and exits 0,
which this project has already had (e1e577a). Caught the same way:
`tests/playwright/scripts/assert-spec-coverage.sh` compares the specs on disk
against the files `playwright test --list` resolves, and fails on any difference
or on an empty list.

It was verified by adding a stray `tests/stray.spec.ts`, watching the guard fail
and name the file, then removing it and watching it pass. An unexercised guard
is not a guard — that is the same lesson as the tf-validate discovery check, and
it cost thirty seconds to apply here.

## Two processes, not one

The end-to-end claim is deliberately not made by the browser alone. The
regression creates `$UI_PROBE_NAME` through the UI and does not delete it;
`app/scripts/assert_ui_write.py` then connects straight to PostgreSQL and looks
that row up. The browser drove HTTP, the assertion reads SQL, and only both
together support the sentence "a UI action reached RDS".

`UI_PROBE_NAME` is required and has no default. A default would let the script
pass while checking a name nobody created — a check that cannot fail, which is
worse than no check.

In AWS the assertion has to run as a one-off ECS task, because RDS is not
reachable from a GitHub runner. That needed environment overrides in the
run-task helper, which existed in two copies — one in `deploy-stage.yml`, one in
`promote-prod.yml`. Exactly the change that lands in one copy and not the other,
so the loop moved to `scripts/ecs-run-task.sh` and both workflows now call it.
The invariant "a fix to a shared invariant goes to every environment in the same
commit" is easier to keep when there is only one place to fix.

## Smaller things worth remembering

- **httpx trusts the environment by default.** The contract suite failed all 19
  cases in a sandbox that exported a SOCKS proxy, on an unrelated import error.
  `trust_env=False` now pins the suite to the target it was pointed at: these
  tests assert on the behaviour of one named URL, and an ambient proxy turns a
  green run into a statement about something else.
- **The duplicate is decided by the unique constraint**, caught as an
  `IntegrityError`, not by a SELECT before the INSERT. Check-then-insert is a
  race where two concurrent requests both pass the check and one returns 500
  where the contract promises 409.
- **`ORDER BY id` is explicit**, because an unordered SELECT has no guaranteed
  order in PostgreSQL and a positional assertion would then depend on physical
  row layout.
- **The list response is an envelope.** Pagination is Phase 16; adding
  `limit`/`offset`/`total` to `{items, count}` is additive, to a bare array it
  is a breaking change to every consumer and every test.
- The API tests speak HTTP to a running app rather than importing FastAPI
  in-process, so they exercise the image, the network and a real database — the
  property that lets the same file serve as the gate against deployed stage.
- They need a virtualenv on the devbox: Ubuntu 24.04 marks the system
  interpreter externally-managed (PEP 668), and pytest has no business in the
  application image. `make test-api` builds `.venv-api/` and it is gitignored.

## Preflight performed in the chat sandbox

Not a substitute for the devbox run, but it moved four defects earlier than a
round trip:

```text
19/19 contract tests pass against the app on SQLite
playwright --list resolves 5 tests in 2 files across both projects
assert-spec-coverage passes clean, fails on a stray spec, passes again
```

The SQLite harness cannot create the table from the model: SQLite only
autoincrements an INTEGER primary key, and `demo_items.id` is BIGINT (BIGSERIAL
on PostgreSQL). The table was created by hand for the preflight. That is a
harness limitation, not an application one, and it is the reason this preflight
does not replace `make local-up` on the devbox.

## What is NOT done

- Nothing has run against PostgreSQL. `make local-up`, `migrate`, `seed`,
  `test-api`, `test-smoke`, `test-regression`, `test-db` and
  `test-spec-coverage` are all still owed on the devbox.
- Nothing has run against AWS. The phase's closing criterion — the regression
  green in CI against Compose, the read-only smoke green against deployed prod,
  and the DB assertion proving a UI action reached RDS — is unmet until a
  `deploy-stage → destroy` cycle runs.
- Per the standing invariant, destroy must pass end-to-end at the end of this
  phase too, not only at the end of the MVP.

## Debt noticed, not fixed

- `tests/db/assert_seed.py` and `app/scripts/assert_seed.py` are still two
  copies of one assertion. This session did not add a third: the UI-write
  assertion exists only in the image and is invoked from there by both the
  Makefile and the workflow.
- `docs/next-phases.md` §11.0 says the gitleaks full-history run is still owed;
  `docs/discussion-log.md` says publication was preceded by a full-history
  sweep. Both cannot be right. One of them needs correcting, and the sweep needs
  re-running under gitleaks proper if it was not.
