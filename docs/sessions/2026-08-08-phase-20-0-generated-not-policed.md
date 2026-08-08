# 2026-08-08 — Phase 20.0: the picture gets generated, not policed

A planning session that found its own subject in the first ten minutes. It
opened intending to decide what comes after Phase 19 — the plan ended at 19 and
nothing claimed the cursor forward — and instead found five reader-facing
documents describing a live, publicly-pressed, closed phase as unbuilt. The
picture the session then went on to design is the fix for that, rather than a
feature that happens to sit next to it.

## The finding: five places, and none of them reachable by a gate

`infra/self-service` was applied in 19b, pressed anonymously in 19c and closed
by 19g. These said otherwise:

```text
README.md:142-152          "NOT APPLIED", "has never been applied",
                           "Until then the button does not exist"
docs/architecture.md:61    "written and not applied ... nothing in AWS answers
                           for it yet"
docs/architecture.md:74    the Mermaid node: "WRITTEN, NOT APPLIED"
docs/cost-control.md:118   "Worst case if the button is ever public
                           (Phase 19, NOT BUILT)", and "None of this is running"
docs/interview-talking-points.md:22,30,180
                           "five are live", "written not applied",
                           "planned, not built ... designed, not shipped"
site/index.html:243        "Five Terraform state levels" — on the live page,
                           standing on the sixth
```

README contradicted itself: line 14 already knew the level was applied in 19b and
pressed in 19c while line 148 said it had never been applied. A sixth place fell
out on the way past — `docs/architecture.md`'s heading said "seven state levels",
correct while there were five permanent ones and never revisited. README had
already been updated to eight.

**Why no gate saw it.** `make docs-check` verifies that every `make` target,
repository path, HTTP route and workflow filename a document NAMES exists. Every
one of these documents named only real things. What was false was what they
CLAIMED, and no check in this repository looks at claims.

This is the third arrival of the species in three days and the largest by an
order of magnitude. 19g found two documents agreeing with each other and not with
the control store. This found five, in the files an outside reader actually
opens, on a public repository, for six days.

## What the session refused to do about it

Write a bigger linter. A check for the phrase "not applied" would have caught
exactly this instance and nothing else — the next stale claim will be a number,
a count, or a tense.

**ADR-0039 D1 removes the class instead.** The architecture section is generated
from `infra/`, so it can be wrong only if the generator is wrong, and the
generator gets a drift gate that has to be broken on purpose before it counts.
The prose survives only as a second rendering of the same generated file: a text
block maintained beside the map is the sixth stale place, pre-arranged.

## The phase this became

Asked for: a visual panel with AWS iconography showing which services come up
and come down in what order, per-phase and per-cycle estimates, and which tests
run and what they assert — all without opening a log. **ADR-0039** records four
decisions and `docs/next-phases.md` the split into 20a–20d.

```text
D1  the map is generated from the repository; drift is a CI gate
D2  order, duration and identity come from terraform's own -json event stream,
    not from a hand-written mapping of workflow step to service
D3  cost is COMPUTED from measured seconds and a dated rate table, labelled as
    computed, and reconciled once against a real bill
D4  the map is permanent; run state is a layer on it - absent / at rest / live
```

D4 is the one the session got wrong first. The chat proposed a replay panel on
the reasoning that a cycle lasts fifteen minutes and the account is empty the
rest of the time, so a live panel shows emptiness. Corrected on the spot, and the
correction is better: the map is always the page. At rest it carries the last
measured cycle with its date and numbers, which is what a visitor sees almost
always and is exactly what makes it worth opening.

Two things fell out of the correction that the plan did not have:

- **an identifier is not an ARN.** Terraform's `apply_complete` carries
  `id_key`/`id_value` — the provider's id. For `aws_lb` and `aws_ecs_service`
  that IS an ARN; for `aws_db_instance` it is the instance identifier; for a
  security group, `sg-…`. The page shows the identity a resource was given, and
  does not promise an ARN it was never handed. (Publishing them exposes nothing
  new: `docs/security-posture.md` already treats account ids and role ARNs as
  identifiers, and the page has printed the account id since 11.1b.)
- **live pulsing has a role problem.** Per-resource pulsing needs the timeline
  published DURING the apply, and the only step holding credentials then holds
  the deploy role — which ADR-0026 deliberately keeps away from the bucket that
  reports on it. So live is per PHASE, from the Actions API, which costs no new
  permission at all; per-resource detail lands at the end of the apply step. The
  two ways to buy more are priced in the ADR and neither is taken by default.

## Checked rather than assumed

- `terraform apply -json` really does emit `apply_start` / `apply_progress` /
  `apply_complete` / `apply_errored` per resource with an RFC3339 timestamp, the
  address, the action and `elapsed_seconds`. Read from HashiCorp's
  machine-readable-UI reference, not from memory. That `destroy` behaves the same
  way is an expectation, and 20b's first run is what confirms it.
- The AWS Architecture Icons set is licensed for creating architecture diagrams,
  and AWS's own examples are whitepapers, presentations, data sheets and posters.
  A public web page is neither named nor excluded. 20a establishes the answer or
  uses project glyphs; it does not guess.
- **A cost figure was invented and caught.** The first draft of the cost-control
  fix put "$0.09" against 19c. `$0.09` and `$0.17` are 16a's and 16b's cycles.
  19c has no recorded cost figure at all — the phase closed without one. The
  document now says so, because a gap in the record is not a zero, and 20d exists
  partly so the gap stops recurring.

## True now

- Phase 19 closed; Phase 20.0 closed with ADR-0039 and the 20a–20d plan
- five documents corrected, delivered as their own patch ahead of the plan
- nothing applied, no environment existed at any point, **$0**
- next allowed step is **20a**, which applies nothing and costs nothing

## Gotchas

- The chat's clone was fresh and equal to `origin/main` at `264704a`, four
  minutes old. The previous session had closed at 01:04 UTC and this one opened
  at 01:09 — the one case where a stale sandbox clone was not the risk, and it
  was checked anyway.
- `docs/cost-control.md` and `docs/interview-talking-points.md` are NOT in
  `docs-check`'s document list (README, architecture, demo-script, phase-gates,
  session-primer, transfer-buffer). Two of the five stale places were in files
  the gate does not even open — worth knowing before assuming a green
  `docs-check` says anything about them.
