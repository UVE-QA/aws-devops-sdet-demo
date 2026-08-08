# ADR-0040: The at-rest numbers outlive a cancelled run, and the join happens on the runner

## Status
Accepted (Phase 20b.2, 2026-08-08). Implements ADR-0039 D4; changes nothing in
ADR-0026, whose rule about sources it inherits. Both decisions below were found
by writing the CONSUMER of 20b.1's timeline rather than by planning it — neither
is in `docs/next-phases.md`, and the timeline format they act on is unchanged.

## Context

20b.1 captured Terraform's `-json` event stream, folded it into a timeline per
environment per job, and published two objects: one keyed by run id and job,
immutable, and `latest.json`, overwritten every time. `scripts/publish-status.sh`
called `latest.json` "the map's at-rest source", and nothing drew it yet, so the
description cost nothing.

Then the page was written, and it did.

ADR-0039 D4 says the at-rest state is the one a visitor almost always sees,
because a cycle lives about fifteen minutes and the account is empty the rest of
the time — and that at-rest carries "the last measured values… and the DATE of
the cycle they came from". `latest.json` cannot be that. It is written by every
run whatever happened, including the cancelled one whose timeline is deliberately
marked `incomplete`. One cancelled run would replace a dated, complete
measurement with a scatter of nodes that stopped mid-apply, and the page would
show the difference as absence — for a reason no visitor could see.

That is 20b.1's own claim turned against the page: *a run that dies mid-apply
must not be reported as a cycle that happened.* It was enforced in the fold and
then thrown away by the publish rule one step later.

The second question arrived with the same code. Terraform reports RESOURCES —
`module.rds.aws_db_instance.this[0]` — and the map draws SERVICES. Something has
to decide which resource belongs to which node, and the obvious place was the
page, which already fetches `topology.json` and could fetch a timeline beside
it. That rule would then exist in JavaScript on the page and in Python in
whatever gate checked it. This repository has been bitten by exactly that shape:
`docker compose config --images app` filtered by service on the devbox and
ignored the filter on the GitHub runner, and the Makefile recipe was
byte-identical on both machines.

## Decision

### D1 — two objects, because there are two questions

```text
timeline/<env>/latest.json         what happened LAST, any status. Read for its
                                   status, never for its numbers
timeline/<env>/nodes-apply.json    what the last cycle that FINISHED measured,
timeline/<env>/nodes-destroy.json  joined onto the map's nodes. Published only
                                   when the timeline's status is `complete`
```

The page draws the second and says the first. After a cancelled run it reads:
*the most recent run did not finish; the figures below are from the last cycle
that completed, dated …* — which is more informative than either object alone,
and is the same sentence the fold has been able to justify since 20b.1 without
anywhere to say it.

The kind is in the key because an apply and a destroy measure different things
and would otherwise overwrite each other: an apply lights the service nodes, a
destroy lights the teardown node.

**This makes the live break test visible.** 20b.2 has to prove that a cancelled
RUN publishes INCOMPLETE — a thing fixtures cannot show, because they prove the
fold and not the workflow's `if: always()`. With this split the proof is a
sentence on the public page rather than a JSON object someone has to fetch.

### D2 — the join is a script on the runner, not a few lines on the page

`scripts/node-states.py` reads `site/data/topology.json` and one timeline and
writes node states. The page is left a renderer: what it fetches is already node
states, and the only thing it decides is how to draw them.

The rule it holds, in full:

```text
a node        the address is in some node's `members`, FOR THIS ENVIRONMENT.
              Every `[...]` is stripped first, because count and for_each are
              properties of an apply while `members` comes from a static read of
              infra/. The environment filter is not tidiness: stage and prod are
              the same modules in two state levels and hold identical member
              addresses, so an unfiltered index would light half the map from
              the other environment's cycle
the teardown  action `delete`. That node stands for a whole state level and has
              no member list, so a delete is matched by environment
not shown     the address belongs to a group ADR-0039 D1 deliberately does not
              draw. Recorded, counted, quiet
unknown       nothing claims it. Printed in the apply log, carried onto the page,
              and counted by a gate
```

`make node-states-check` is that gate, in `ci.yml`. Its claim is ADR-0039 D1's
coverage rule applied to observations instead of to the repository: **a resource
a cycle created is drawn, is recorded as deliberately not drawn, or is reported
as unknown — never silently absent.**

### D3 — a node's numbers are derived, not mapped

```text
duration   first apply_start in the group to the last apply_complete. ADR-0039
           D5's middle row: the node is busy while ANY of its members is in
           flight. Exact, not an approximation
identity   the id_value of the member that took the LONGEST, when it carries one
```

The alternative to the second was a table — *for RDS show the instance, for the
ALB show the load balancer* — and a table like that is a claim. The derived rule
gives the same answers for all three of the nodes anyone would check, because
the resource that dominates a node's duration is the one the node is mostly
about. Nothing is enriched into anything and no AWS call is made (ADR-0039 D2).

### D4 — the live pulse is bound to a step, and the binding is checked

Every workflow here holds ONE job, so a job name cannot tell `Build` from
`Apply — stage`: the phase→live binding names a STEP. Those bindings live in
`assets/topology-groups.json`, which is the file ADR-0039 D1 already reserves
for what cannot be derived, and `scripts/generate-topology.py` REFUSES if a
binding names a workflow, job or step that does not exist.

Without that check, renaming a step would break the pulse silently and no gate
in this repository could see it — the failure would be a picture that simply
never lights, which is indistinguishable from a quiet week.

The map does not read the Actions API itself. The dashboard script on the same
page already does, and 60 anonymous requests per hour per IP is the whole budget
(ADR-0026); a second reader would halve the rate at which either notices
anything. The observation is handed over as a DOM event, so the two scripts stay
ignorant of each other's identifiers, which is the property the map's own
comment asks for.

## Consequences

- `latest.json` stops being described as the at-rest source, in
  `scripts/publish-status.sh` and in `docs/architecture.md`. It keeps its job.
- A cancelled run now has a visible, honest rendering on a public page, and the
  20b.2 break test has somewhere to be seen rather than only somewhere to be
  fetched.
- The map can render a node state — `incomplete` — that the publish rule
  currently prevents from ever reaching it. The branch stays anyway, and the
  page says why: the alternative to a guard is not "nothing renders", it is
  `undefined` seconds on a public page, which is precisely what happened in 20a
  the last time a state arrived that the renderer had no branch for.
- `MAXDUR`, the constant scaling every bar on the map, was `261` — a figure
  measured once by hand and written into the page. It is now computed from
  whatever cycle is on the page. A hard-coded measurement inside the file that
  ADR-0039 made generated is the same defect one level down.
- One number the map draws is still not observed: cost. It stays absent until
  20d gives it a dated rate table and the label COMPUTED (ADR-0039 D3).
- `tests/fixtures/timeline/cases/apply-module` is added, and with it the answer
  to the last piece of Terraform's schema that 20b.1 had to read from the
  documentation. It costs nothing: a local module holding `terraform_data` is as
  real a terraform run as the others. The consequence worth writing down is the
  general one — **a question about a tool's own output is usually answerable
  offline, and answering it before the billable run turns a discovery into a
  confirmation.**
