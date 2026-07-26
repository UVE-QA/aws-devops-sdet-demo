# ADR-0025: Read-only and destructive suites are separated by directory, not by convention

## Status
Accepted (Phase 10). Refines the stage/prod split of ADR-0017 D2a.

## Context

Phase 10 adds the first destructive tests this project has ever had: a Playwright
regression that creates and deletes items through the UI, and an HTTP contract
suite that does the same over the API. Until now every test was read-only, which
is why the question this ADR answers had never come up.

Both stage and prod run Playwright. stage is seeded and disposable; prod is the
promoted environment on a public HTTPS name, and it is the artifact an
interviewer is pointed at. A destructive spec must never run there.

The separation already appeared to exist. `promote-prod.yml` carried a step
named "Read-only smoke against prod" with the comment:

```text
# Read-only on purpose. Destructive regression belongs to stage, which
# is seeded and disposable; prod gets the smoke that proves the
# promoted image serves traffic and reaches its database.
```

and then ran:

```bash
npx playwright test
```

which executes the entire `testDir`. The comment described an intention; the
command had no way to honour it. The property held only because no destructive
spec existed yet, and the first one added — in this phase — would have silently
made prod destructive while the comment claiming otherwise stayed exactly where
it was, still reading as a guarantee.

This is the project's documented failure mode restated once more: **"it looked
finished" rather than "it broke"**. Nothing would have gone red. The first
symptom would have been rows appearing and disappearing in prod.

## Decision

The suites are separated by **directory**, and the directories are bound to
Playwright projects in `playwright.config.ts`:

```text
tests/playwright/tests/smoke/        project "smoke"       read-only
tests/playwright/tests/regression/   project "regression"  destructive
```

Every caller names the projects it wants, explicitly:

```text
promote-prod.yml   npx playwright test --project=smoke
deploy-stage.yml   npx playwright test --project=smoke --project=regression
ci.yml             make test-smoke, then make test-regression
```

No caller relies on "run everything". stage's step names both projects rather
than omitting the flag, so a third project added later joins stage only when
somebody decides it should.

The API contract suite (`tests/api/`) is destructive by nature and has no
read-only half. It runs in CI and against stage, and is simply absent from
`promote-prod.yml`.

## The part that makes it hold

A directory convention that nothing enforces is a comment with a longer name. A
spec file placed outside both directories matches neither project, so Playwright
runs it in **no** project and reports nothing about it — a test that silently
does not exist, and green everywhere.

That is the same shape as a `make tf-validate` that discovers zero root levels
and exits 0, which this project has already had (e1e577a). It is caught the same
way, by asserting on the discovery instead of trusting it:

```text
tests/playwright/scripts/assert-spec-coverage.sh
```

compares the spec files on disk against the files `playwright test --list`
actually resolves, and fails when they differ or when either list is empty. It
runs in `ci.yml` and in `deploy-stage.yml`.

The check was verified by breaking it on purpose — a stray `tests/stray.spec.ts`
was added, the script failed and named the file, and passed again once it was
removed. An unexercised guard is not a guard.

## Consequences

- Placing a spec is now a decision with a visible consequence, made at file
  creation time, not a habit that erodes.
- prod's read-only guarantee is enforced in two independent places: the project
  selection in the workflow, and the coverage check that no spec escapes the
  projects.
- One more thing to know when adding a test. Accepted: the alternative is a
  guarantee that depends on everyone remembering a comment.
- The Playwright HTML report from a stage run contains both suites, because
  `deploy-stage.yml` runs them in a single invocation. Two invocations would
  leave only the second in `playwright-report/`, and the artifact would quietly
  under-report what ran.
