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

Five decisions, taken together because each one is only safe given the others.
D5 arrived after the first four and changed the shape of D1's gate; it is
recorded in place rather than as an amendment, because none of this had shipped.

### D1 — the picture is generated from the repository, and drift is a gate

The map's skeleton — state levels, the resources each module declares, the
suites, the workflow steps — is generated into `site/data/topology.json` by a
checked-in script. A `make site-data-check` target regenerates and compares; CI
runs it.

**The gate checks coverage, not depiction**, and the difference is what makes it
compatible with D5's one-screen constraint. It does not require that every
resource in `infra/` be drawn — infrastructure grows and the screen does not. It
requires that every resource in `infra/` be assigned to exactly ONE display
group, including the group meaning "deliberately not shown". An unassigned
resource is a red build; a resource someone decided to hide is green and
recorded.

That is the **spec-coverage guard's shape**, which this repository already runs
over the Playwright suites: a spec belonging to no suite fails the build rather
than being silently reported by nothing. Here, a resource belonging to no group
fails the build rather than being silently absent from the picture.

It is also `make docs-check`'s shape one level up: that gate checks that what a
document NAMES exists; this one checks that what the repository CONTAINS has been
decided about.

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

**Identity is whatever the stream hands over, and nothing is chased.** The page
shows `id_value` when `apply_complete` carries one and shows nothing when it does
not. For `aws_lb` and `aws_ecs_service` that happens to be an ARN, for
`aws_db_instance` it is the instance identifier, for a security group `sg-…`; the
page does not care which, does not label them all "ARN", and makes **no extra AWS
call** to enrich one into another. An ARN is not a goal — it is one of the shapes
a cheaply-available identity takes.

Publishing them on a public page changes no exposure:
`docs/security-posture.md` already treats account ids and role ARNs as
identifiers rather than credentials, and the page has printed the account id in
every environment header since 11.1b.

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

### D5 — the drawing may approximate; the data behind it may not

Added the same evening, after the first four were written. The requirement is
**one screen, no scrolling** — legibility beats fidelity, and anyone who wants
exactness has the text chronometry a click away. Taken naively that contradicts
D1, which exists precisely so the picture cannot say something untrue. It does
not, once the line is drawn in the right place:

```text
generated, exact       which nodes exist, that they exist, the order events
                       actually happened in, the measured numbers
aggregated, exact      a node is a SERVICE, not a resource. It is busy while
                       ANY of its resources is in flight, and its duration runs
                       from the first apply_start in the group to the last
                       apply_complete. Computed, not estimated
editorial, approximate the layout, and any non-linear rendering of duration -
                       a four-second security group and a four-minute database
                       cannot share one screen at true scale
```

**The middle row is the one the requirement is actually about**, and it is worth
separating from the third because it is not an approximation at all. A service a
reader recognises is several Terraform resources — RDS is an instance, a subnet
group and a parameter group; the ALB is a load balancer, a target group and a
listener; ECS is a cluster, a task definition and a service. The map draws one
node per service and shows it as active, without splitting it into the internal
steps that got it there. Anyone who wants those opens the text chronometry, where
every resource keeps its own line.

Note what is NOT available to drop: Terraform reports resources, not a service's
own lifecycle. RDS moving `creating → backing-up → available` never reaches the
stream — `apply_progress` only counts the seconds Terraform spent waiting. So
service-level granularity is the finest the page could honestly draw anyway; the
decision is to stop there rather than to discard something we had.

So approximation is permitted and BOUNDED: bounded by generated data, never
free-hand. A node may aggregate several resources; it may not contain a service
the repository does not have, or omit one without the coverage gate above having
been told.

Anything approximated says so where it renders, and links to the exact rendering.
An unlabelled approximation is a claim, which is the thing this ADR exists to
stop.

**One screen means one DESKTOP screen.** A map of six permanent levels, a
per-cycle environment and seven phases does not fit a phone at any layout, and
pretending otherwise produces either a scroll or an unreadable diagram. On narrow
viewports the map degrades to the text chronometry instead. That gives the prose
rendering of D1 an actual job rather than a courtesy: it is the small-screen
version, and it is generated from the same file, so it cannot drift from what the
map shows.

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
