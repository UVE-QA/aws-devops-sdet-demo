# Timeline fixtures

Input for `make timeline-check`, the gate over `scripts/fold-timeline.py`
(ADR-0039 D2).

## These are real terraform runs, not hand-written JSON

Every `.jsonl` under `cases/` is the actual `-json` output of a terraform
invocation, produced by `tests/fixtures/timeline/generate.sh`. None of it was
typed from the documentation.

That is the point. The thing under test is a fold of *Terraform's* event
schema, and a fixture invented from a reading of the docs would only ever test
what its author believed the schema to be. This repository has a name for the
failure that produces: a break test that fails to break is testing your
assumption about the tool.

Two examples of what the real streams said and a written fixture would not
have:

- an apply from a saved plan file — the shape `deploy-stage` and
  `promote-prod` actually use — emits **one** `change_summary`, not two, because
  the plan half already happened;
- an apply that FAILS emits a `change_summary` whose operation is `"plan"` and
  never reaches the terminal one, so a fold reading only the stream would label
  a half-finished apply a plan. That is why `tf-stream.sh` records the arguments
  it was given in a `.cmd` file: what was RUN is a fact the runner has and the
  stream does not.

## They cost nothing and touch no cloud

Every resource in them is the built-in `terraform_data`, which needs no
provider plugin. `terraform init` runs offline, no AWS credential is involved,
and nothing is created outside a temporary directory.

## What each stream carries

`scripts/tf-stream.sh` writes three files per invocation, and `generate.sh`
reproduces all three:

```text
NN-<label>.jsonl   the event stream          created BEFORE terraform starts
NN-<label>.cmd     the terraform arguments   written BEFORE terraform starts
NN-<label>.rc      the exit code             written AFTER terraform returns
```

The `.jsonl`/`.rc` pair is what makes an honest verdict possible. A stream with
no `.rc` beside it means terraform never returned — cancelled, killed, runner
lost — and no amount of plausible-looking events outweighs that.

## The cases

```text
apply-complete    a plain apply that finished
apply-from-plan   plan to a file, then apply that file: ONE change_summary
apply-errored     a resource fails; the ones depending on it never start
apply-killed      terraform KILLED mid-apply. No .rc was ever written, one
                  resource started and never finished. The case the gate
                  exists for
destroy-cycle     destroy.yml's shape: a targeted destroy, then the full one.
                  Two operations, one timeline, and the targeting warnings are
                  warnings rather than errors
```

`apply-killed` is not a truncated file. `generate.sh` starts a real apply whose
second resource sleeps, and kills the process while it is in there.

## Regenerating

```bash
tests/fixtures/timeline/generate.sh
make timeline-check
```

`cases/GENERATED-BY` records the terraform version that produced them, so a
fixture cannot quietly claim to have come from a version it did not.

`expected.json` is compared by summary, not byte-for-byte: statuses, counts,
per-resource verdicts, diagnostic counts, and the health of the stream itself.
Timestamps, ids and durations differ on every generation, and a gate that had to
be regenerated after every run would be switched off within a week.
