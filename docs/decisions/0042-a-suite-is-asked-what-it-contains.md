# ADR-0042: A suite is asked what it contains, and given a collector if it has none

## Status
Accepted (Phase 20c, 2026-08-08). Fills in ADR-0039 D2b, which put a node per
suite on the map and left what those nodes say for this phase. Uses ADR-0025's
directory binding as a checkable property rather than as a convention.

## Context
Since 20a every suite has a node on the map. What each node said about itself
came from two places, and neither is evidence:

```text
asserts       a sentence per suite in assets/topology-groups.json, written by
              hand next to the suite it describes
spec_files    a count of FILES, from a glob
```

The sentence is the exact shape Phase 20 exists to end. On 2026-08-08 eleven
reader-facing places described an applied, publicly-pressed state level as
never applied, and the reason nothing caught it is that no linter checks whether
a sentence is still TRUE. The count is worse than it looks: two spec files can
hold two tests or twenty, and `tests/api` — two files — holds fifty-two.

`docs/next-phases.md` named the method: collect from `pytest --collect-only` and
`playwright --list`. Reading the repository before writing any code found three
things that method does not survive.

**`tests/db` has no collector.** `assert_seed.py` is not a pytest module; it is a
standalone script whose checks are statements inside one function, printing
PASS/FAIL, run inside the application image by `docker compose` locally and as an
ECS task in AWS. `pytest --collect-only` finds nothing there. One suite of the
five was outside the method entirely.

**The map's gate has no test dependencies.** `make site-data-check` runs in
ci.yml's `terraform-checks` job, which installs Terraform, Python and Checkov.
Collection needs the application's requirements, the api venv, Node and
Playwright — all of which the `local-ci` job installs and that job does not.

**There are two copies of the db assertion, and the cloud runs the other one.**
`tests/db/assert_seed.py` is the local `make test-db` gate;
`app/scripts/assert_seed.py` is baked into the image and is what the
`suite.db.stage` and `suite.db.prod` nodes actually observe. The two are asked to
mirror each other by a comment at the top of each file, and had been for eleven
phases.

## Decision

### D1. A suite is ASKED. A suite that cannot be asked is given the ability
The inventory comes from the tools that run the suites, normalised by
`scripts/collect-suites.py` into `site/data/suites.json`:

```text
pytest --collect-only -q     tests/unit, tests/api
playwright test --list       tests/playwright/tests/{smoke,regression}
assert_seed.py --list        tests/db
```

The db suite got the third of those rather than a description. Its checks are now
a list of named callables; `--list` prints the list and the run executes the same
list, so the inventory and the program cannot disagree without one edit in one
place. Each check's own docstring is the sentence the map shows — read from the
check, not maintained beside it.

**Rejected: parse the files.** A regex over `def test_` and `test("…")` needs no
dependency and runs anywhere, including in the map's own job. It is also a SECOND
definition of what a test is, true until the first parametrised case, skip mark
or generated title — and this project has already paid for a second definition
(`docker compose config --images app`, which handed the image scan
`postgres:16`). The tools are the definition; the script only normalises.

### D2. The gate runs where the dependencies are
`make suite-inventory-check` is the last step of ci.yml's `local-ci` job, after
the steps whose side effect is the venvs and `node_modules`. It does not join
`make site-data-check` in `terraform-checks`. The map's data and the map's
inventory are therefore gated in two different jobs, which is the price of D1 and
is cheaper than either installing the world twice or parsing the files.

### D3. The collected versions are part of the answer
The pinned versions are read from `tests/*/requirements.txt` and
`tests/playwright/package.json`, compared against the tool actually invoked, and
recorded in the output. Discovery through a tool is a version-dependent fact:
`docker compose config --images app` filtered by service on the devbox and
ignored the filter on a GitHub runner, with a byte-identical recipe. A host
collecting with a different pytest is told which two versions differ, instead of
being handed a diff of 780 lines of JSON.

### D4. The mirror is asserted, and the observed copy is the one AWS runs
Both copies of the db assertion are collected and compared; a disagreement is a
refusal. The inventory published for the `db` node is the one from
`app/scripts/assert_seed.py`, because that is the file stage and prod execute. An
inventory taken from the local copy would be a true description of a program the
cloud does not run — the same class of defect as a document that is true about a
plan and false about an account.

### D5. The inventory is not the results, and they live in separate files
`site/data/suites.json` is a property of the REPOSITORY: it changes when a test
is added, renamed or deleted, and it is gated by regeneration. Results —
passed, failed, duration — are a property of a RUN, they arrive from the
published reports, and they belong beside the timeline in the bucket, not in a
committed file. A node with an inventory and no result renders as not observed,
never as green: an empty result is not a clean result, which this project has now
recorded four times.

## Consequences

- `make suite-inventory` / `make suite-inventory-check`, and one new step in
  ci.yml's `local-ci` job. Adding, renaming or deleting a test now requires
  regenerating a committed file, exactly like adding a resource to `infra/`.
- `assets/topology-groups.json` keeps its `asserts` sentences for one more patch,
  until the map reads the inventory; then they go, and the file returns to being
  purely about grouping and arrangement.
- The two copies of the db assertion can no longer drift silently. They can still
  both be wrong together — the gate asserts that they agree, not that they are
  right.
- Collection costs about 35 seconds in CI, almost all of it Playwright's
  TypeScript compile, and nothing in AWS.

### The refusals, each fired on purpose
Recorded in `docs/sessions/2026-08-08-phase-20c-the-suites-answer-for-themselves.log`,
with a green control before the first and after the last:

```text
a test renamed, inventory not regenerated      DRIFT
the two copies of the db assertion disagree    REFUSED, both lists printed
the db check list emptied                      REFUSED, "refusing to report zero"
a pytest suite with its files moved away        REFUSED, but see below
the pinned pytest is not the one on the machine REFUSED, both versions named
a spec answering to a project from outside its
  directory (ADR-0025's binding, violated)      REFUSED
the map naming a suite nothing can collect      REFUSED
```

**The zero-tests refusal is unreachable for the pytest suites, and the break test
is what said so.** pytest exits 5 when it collects nothing, so the
collector-failed refusal fires first and prints pytest's own `no tests collected`.
The outcome is red either way and the message is readable, so the check stays —
but its stated reason is now known to be true only for the db suite. A gate whose
justification has never been exercised is a gate that has only ever been seen
green.
