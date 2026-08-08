# ADR-0039: The cycle is visible without a log, and the picture is generated

## Status
Accepted (Phase 20.0, 2026-08-08). Extends ADR-0026, whose rule about sources it
inherits unchanged. Does not amend ADR-0027; the dashboard level is untouched.

## Context

The dashboard answers "where is the cycle" and "what exists in AWS" (ADR-0026).
It does not answer the question a reader actually arrives with, which is **what
this project DOES**: which AWS services a cycle creates and destroys, in what
order, how long each takes, what it costs, and what the tests assert. Today that
lives in a hand-written section of `site/index.html` — seven text chips and two
paragraphs — and in `docs/architecture.md`, and anyone who wants more has to open
a GitHub Actions log they may not have access to.

The session that decided this phase opened by finding that same hand-written
section telling every visitor there were **five** permanent state levels while
standing on the sixth, alongside four other documents describing a live public
button as unbuilt. `make docs-check` could not see any of it: it verifies that
every path, target and route a document NAMES exists, never that what a document
CLAIMS is true. So the phase has two problems, not one, and the second is the
harder: **a richer picture maintained by hand is a bigger surface for exactly the
defect that was just found.**

## Decision

Four decisions, taken together because each one is only safe given the others.

### D1 — the picture is generated from the repository, and drift is a gate

The map's skeleton — state levels, the resources each module declares, the
suites, the workflow steps — is generated into `site/data/topology.json` by a
checked-in script. A `make site-data-check` target regenerates and compares; CI
runs it. A module that gains a resource and a page that does not mention it is a
red build, not a discovery six weeks later.

This is `make docs-check`'s shape applied one level up: that gate checks that
what a document names EXISTS, this one checks that what the page draws is what
the repository CONTAINS.

A hand-drawn SVG was the alternative, and it is prettier. It is also the same
class of artifact as the five places this session had to correct.

**The prose survives, on one condition.** A text rendering of the same chronology
may stay on the page — it reads better than a diagram for anyone who wants the
sequence in words — but it is rendered from `topology.json` too. One source, two
renderings. A prose block maintained separately is the sixth stale place.

### D2 — order and duration come from Terraform's own event stream

`terraform apply -json` and `destroy -json` emit `apply_start`,
`apply_progress`, `apply_complete` and `apply_errored` per resource, each with
an RFC3339 `@timestamp`, the resource address, the action, `elapsed_seconds`,
and — on completion — the `id_key`/`id_value` the provider assigned. A script
folds that stream into `timeline/<environment>/<run id>.json`, which
`scripts/publish-status.sh` publishes exactly as it already publishes the
Playwright report.

The alternative was a hand-written mapping from workflow step to service list.
That mapping would be a claim about what a step does; the event stream is the
step's own account of what it did. ADR-0026's rule — a source may only assert
what it observes — settles it without further argument.

**What the page may call an identifier.** `id_value` is what the provider uses as
the resource id: for `aws_lb` and `aws_ecs_service` that is an ARN, for
`aws_db_instance` it is the instance identifier, for a security group it is
`sg-…`. The page shows the identity a resource was given at creation and does
not promise an ARN it was never handed. Where a true ARN is wanted for its own
sake, `scripts/observe-environment.sh` already reads them.

Publishing an ARN on a public page changes no exposure: `docs/security-posture.md`
already treats account ids and role ARNs as identifiers rather than credentials,
and the page has printed the account id in every environment header since 11.1b.

### D3 — cost is computed, and says so

Per-resource seconds from D2 multiplied by a dated rate table in the repository,
rendered per phase and per cycle. It is labelled a COMPUTED estimate wherever it
appears, and it is reconciled once against a real bill for one cycle, with the
delta recorded.

ADR-0026's rule applies to money as much as to state: a figure derived from
duration is not an observation of a charge, and a page that renders the two
identically is making the claim this project keeps having to retract. Cost
Explorer would give the observed half, at the price of another credential and a
24-hour delay; deferred, not rejected.

### D4 — the map is permanent; run state is a layer on it

The map is on the page always. A cycle lives about fifteen minutes and the
account is empty the rest of the time, and the wrong conclusion to draw from that
is that the page should show a cycle only when there is one. Every node has three
states:

    absent    nothing has been recorded for it — drawn, dimmed
    at rest   the last measured values: duration, identifier, computed cost,
              and the DATE of the cycle they came from
    live      pulsing while the phase it belongs to is running

At-rest is the state a visitor almost always sees, so it carries the numbers: the
page shows a real, dated, measured cycle without anyone launching anything.

**Live is per PHASE, not per resource, and that is a deliberate limit.** The
GitHub Actions API reports the running job and step live and anonymously, so
phase-level pulsing costs nothing and needs no new permission. Per-resource
pulsing would need the timeline published DURING the apply, and the only step
holding credentials at that moment holds the deploy role — which ADR-0026 keeps
away from the bucket that reports on it, on purpose. Two ways to buy it were
considered and both are deferred to 20b with their price attached: a second role
assumed inside the step for the uploader alone (the split survives; the
complexity is real), or `s3:PutObject` on `timeline/*` for the deploy role (short,
and it spends a separation that no one will remember was deliberate). Per-resource
detail lands at the end of the apply step, minutes into a run, not at the end of
it.

## Consequences

- **The stale architecture section becomes structurally impossible**, which is
  the finding of 2026-08-08 fixed rather than corrected. What replaces it can be
  wrong only if the generator is wrong, and the generator is exercised by a gate
  that has to be broken on purpose before it counts.
- `-json` **replaces the human-readable apply log** in the Actions UI with a JSON
  stream. A step that folds it back into a readable summary is part of 20b, not
  an optional extra: losing a legible apply log to gain a picture would be a bad
  trade, and it would be discovered by someone debugging at the worst moment.
- No new state level, no backend, no credential in the browser. Everything added
  is a generated file in a bucket that already exists.
- The timeline object needs a short `Cache-Control` rather than a CloudFront
  invalidation per write. Invalidations are 1000/month free and then cost money
  and time; a five-second TTL costs neither.
- Publishing a timeline **reduces** pressure on the anonymous GitHub API rate
  limit (60/hour/IP, ADR-0026), because per-resource detail moves to the bucket.
- The AWS Architecture Icons set is licensed by AWS for creating architecture
  diagrams, and the enumerated examples are whitepapers, presentations, data
  sheets and posters — a public page is neither named nor excluded. 20a either
  establishes the answer from AWS's own terms and records it here, or sidesteps
  it with project glyphs. It does not guess.
- Every sub-phase carries a break test, because a gate that has only been seen
  green is indistinguishable from a gate that cannot fail. The two that matter:
  the drift gate must redden on a resource added to a module, and a run that dies
  mid-apply must produce a timeline marked incomplete rather than a plausible
  complete one.
