# Result fixtures

Inputs for `scripts/check-results.py`, the gate over `scripts/fold-results.py`.
Nothing here calls AWS and nothing here costs anything.

## What each case is

```text
no-server-everything-red        REAL. tests/api and both Playwright projects
                                run with nothing listening: 52 failures from
                                pytest, 2 from smoke, 2 from regression and 10
                                specs the run never reached.
db-green                        REAL. app/scripts/assert_seed.py against a
                                seeded database - the copy AWS runs, so the
                                text being parsed is the text a task prints.
db-failed-then-skipped          REAL. The same file against an empty database:
                                FAIL, then SKIP for the check that depends on it.
api-green-hand-written          HAND-WRITTEN, and named so. Derived from the red
                                junit with its failure elements removed, because
                                no green api report exists to record until a
                                cycle produces one. The first live run replaces it.
partial-run-is-incomplete       DERIVED. Three of fifty-two testcases, so the
                                other 49 are not_run and the suite is incomplete.
a-test-the-inventory-does-
  not-have                      DERIVED. A testcase the collectors never saw.
                                It lands in `unknown`, by name, and does not
                                change the suite's verdict.
a-flattened-log-capture-        REAL, and the only fixture here taken from a
  is-incomplete                 live cycle. `aws logs get-log-events --output
                                text` joins the events array with TABS, so the
                                db assertion's two PASS lines and its summary
                                arrived as ONE line and the fold saw one check.
                                The suite had passed; the map said incomplete.
                                The capture is fixed in ecs-run-task.sh; this
                                case pins what the fold does when a capture
                                lies to it - name the gap, never fill it in.
truncated-playwright-report     REAL SHAPE. The JSON reporter's file cut in half,
                                which is what a killed run leaves on disk.
no-node-for-this-environment    The destructive api suite reported for prod.
                                ADR-0025 says it never runs there; the map has
                                no node for it, and the fold refuses.
nothing-reported                No report at all. Refused, because folding
                                nothing produces a page saying everything passed.
```

## Why the inventory here is frozen

`inventory.json` is a snapshot of `site/data/suites.json`, not a link to it, and
`topology.json` holds only the suite node ids the fold looks at. This gate is
about the FOLD. If it read the live inventory, adding one test to `tests/api`
would redden it, and the person who added the test would learn that the fold is
fine and the fixture is stale — which is how a gate teaches people to ignore it.

Regenerating the snapshot is a deliberate act: copy `site/data/suites.json` here
and update the counts in the cases that name them.

## The gate has been broken on purpose

Recorded in `docs/sessions/2026-08-08-phase-20c-the-suites-answer-for-themselves.log`,
with a green control before the first break and after the last:

```text
the fold calls every suite passed              3 of 9 cases red
a test the report never mentioned is dropped   partial-run red, on the count
an unknown test is swallowed, not named        the unknown case red
the cases directory is moved away              REFUSED, not "0 failures"
```
