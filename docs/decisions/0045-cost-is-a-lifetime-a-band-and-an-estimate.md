# ADR-0045 — Cost is a lifetime, a band, and an estimate

- Status: accepted
- Date: 2026-08-08
- Phase: 20d
- Supersedes in part: **ADR-0039 D3**, whose reconciliation clause is narrowed
  below

## Context

ADR-0039 D3 said cost would be "per-resource seconds from D2 multiplied by a
dated rate table", rendered per phase and per cycle, labelled COMPUTED, and
"reconciled once against a real bill for one cycle, with the delta recorded".
20b and 20c delivered the seconds. This is the multiplication.

Three things were settled by reading the data before writing any of it, and each
one contradicts something the plan assumed.

## Decision

### D1 — the meter is a LIFETIME, not a creation

A folded timeline carries `elapsed_seconds` per resource, and it is the obvious
figure to multiply by a rate. It is the wrong figure. `elapsed_seconds` is how
long Terraform took to CREATE the resource; AWS charges for as long as the
resource EXISTS.

The cycle of 2026-08-08 says it plainly:

```text
aws_lb              created in 173s   then stood for 1582 more
aws_db_instance     created in 297s   then stood for  852
aws_ecs_service     created in   1s   then stood for 1143
```

An estimate built on the creation figures would have reported about a ninth of
the load balancer's real cost, and nothing about the output would have looked
wrong. So the meter runs from the create in the APPLY timeline to the delete in
the DESTROY timeline — two runs, and `scripts/fold-cost.py` takes both.

### D2 — it is a BAND, not a number

Terraform reports when it started creating a resource and when it finished. AWS
starts charging somewhere in between and the event stream cannot see where. Both
ends are computed instead of one being chosen:

```text
low     create FINISHED -> delete STARTED     it certainly existed this long
high    create STARTED  -> delete FINISHED    it certainly did not exist longer
```

For the ALB above the two are 1582 and 1772 seconds, five per cent apart. For
RDS they are 852 and 1381 — a 62% spread, because that instance is slow to
create and slow to delete. A single figure would have hidden a real uncertainty
behind two decimal places, which is the failure ADR-0026 named for state and
which applies unchanged to money.

The minimum billing increments are applied to both ends and named where they
bind: RDS bills a deleted instance for ten minutes whatever the clock says. That
is the one direction a pure duration fold can never go — UP — and the cycle it
matters for is the cycle that died early, which is exactly the one somebody would
otherwise report as having cost nothing.

### D3 — prices are captured, shapes are derived, judgement is editorial

Three inputs, three homes, and no file holding two kinds of thing:

```text
site/data/rates.json     CAPTURED from the AWS Price List Query API by
                         scripts/fetch-rates.py. Dated, and every figure carries
                         its SKU and the exact filters that produced it. It
                         REFUSES rather than picks when a filter matches more
                         than one price
scripts/sizing.py        DERIVED from infra/: 0.25 vCPU, 512 MiB, one task,
                         db.t4g.micro, 20 GB. A shape written into a rate table
                         would keep saying 0.25 after somebody raised task_cpu
assets/cost-model.json   EDITORIAL, like assets/topology-groups.json: which kind
                         is worth metering at all, and why the others are not
```

`docs/cost-control.md` had already committed to the first of these in its second
paragraph — costs written "not from a price list assumed rather than checked".
This is that sentence made mechanical.

### D4 — no silent zero

`make rates-check` reads the resource kinds out of `infra/envs/*` and refuses
unless each one is priced, declared free, or named as deliberately not metered.
A NAT gateway added to the network module would cost real money every hour and
would contribute exactly nothing to an estimate that had never heard of it —
and the estimate would still look like an answer. This is ADR-0041's second
discovery channel, read the configuration rather than an index, pointed at money.

The fold has the matching refusal from the other side: a kind it OBSERVES and
cannot price is reported UNPRICED and counted, never folded in as zero. The two
catch different things. The gate catches what the repository declares; the fold
catches what a cycle actually did, which includes anything created outside
Terraform.

### D5 — per-phase cost is an attribution, and most of the money is outside every phase

The plan asked for cost "per phase and per cycle". Per phase is not a property a
lifetime has: an ALB's half-hour cannot belong to the two minutes that created
it. What is well defined is OVERLAP — how much of each lifetime fell inside each
phase's window — and computing it says something the per-cycle figure does not:

**most of a cycle's cost accrues while no phase is running at all.** The
environment is up, the demo is being looked at, nothing is deploying. The fold
reports that remainder as its own bucket rather than distributing it, because
distributing it would be an invention.

### D6 — an estimate is the deliverable; the reconciliation clause is narrowed

ADR-0039 D3 promised one reconciliation against a real bill. That is not being
done, and the promise is retired here rather than left standing in a document:

```text
asked for   an estimate, computed from the price list or from cycles already run
not done    no Cost Explorer credential is added, no billing API is called, and
            no bill is fetched. CE would need another permission in the demo
            account and answers a day late
instead     the estimate says what it is in every rendering - kind
            "computed_estimate", the word ESTIMATE in the summary line, a band
            rather than a figure - and AWS Budgets already watches the actual
            spend from the other side, which is the guard that matters
```

A promise a project has decided not to keep is worse than one it never made:
`docs/next-phases.md` would have kept describing a reconciliation as pending
work for as long as anybody read it.

## Consequences

- `make cost-check` and `make rates-check` run in `ci.yml`, need no credential,
  and cost nothing. `make rates` needs `pricing:GetProducts` and is run by hand.
- **CI is red between this commit and the first `make rates`.** `rates-check`
  refuses a missing table on purpose — a cost gate that passes with no prices is
  the silence D4 exists to end — so the capture belongs in the same push.
- The fold is not wired into any workflow yet. It runs by hand against two
  published timelines; putting it in the destroy job means pairing that run with
  the apply that created what it is deleting, and the pairing rule
  (`nodes-apply.json` is the environment's last apply, by construction) needs its
  own break test before it is trusted.
- The page renders nothing from this yet. `site/data/rates.json` is published
  with the rest of `site/`, so the data is in place when 20e wants it.
- Every figure this produces is a band. Anything that renders one end alone is
  making a claim the fold declined to make.
