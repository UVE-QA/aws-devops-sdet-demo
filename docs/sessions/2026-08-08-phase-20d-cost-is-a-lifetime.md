# 2026-08-08 — Phase 20d: cost is a lifetime, not a creation

Closes 20d's computation half. A cycle's cost is now produced by a command from
the cycle's own timelines and a captured rate table, instead of being worked out
by hand in a session and written into a document.

**ADR-0045.** Break tests in
`docs/sessions/2026-08-08-phase-20d-cost-is-a-lifetime.log`.
Cost: nothing. One free read-only call to the AWS Price List API; no cycle, no
billing API, no environment brought up.

## The mistake that was avoided by reading the data first

`elapsed_seconds` is in every folded timeline, one per resource, and it is the
obvious number to multiply by a rate. It is the wrong number: it is how long
Terraform took to CREATE the resource, and AWS charges for as long as the
resource EXISTS. The real cycle of 2026-08-08 was pulled down and read before a
line of the fold was written:

```text
aws_lb              created in 173s   then stood for 1582 more
aws_db_instance     created in 297s   then stood for  852
aws_ecs_service     created in   1s   then stood for 1143
```

An estimate on the creation figures would have reported a ninth of the load
balancer's cost and would have looked entirely reasonable. So the meter is a
lifetime and spans two runs — the apply that created the resource and the destroy
that removed it — and `scripts/fold-cost.py` takes both.

## The second thing the data settled: it is a band

Terraform says when it started creating a thing and when it finished; AWS starts
charging somewhere in between and the stream cannot see where. Both ends are
computed rather than one being chosen. For the ALB they are 1582 and 1772
seconds, five per cent apart. For RDS they are 852 and 1381 — a 62% spread,
because that instance is slow at both ends. A single figure would have put two
decimal places over a real uncertainty.

## What it says about the cycle of 2026-08-08

```text
cycle CLOSED  20:29:10Z -> 20:59:27Z  (1817s)
ESTIMATE  $0.0183 .. $0.0238

module.alb.aws_lb.this              1582..1772s   $0.0099 .. $0.0111
module.rds.aws_db_instance.this      852..1381s   $0.0045 .. $0.0073
module.ecs.aws_ecs_service.app      1143..1568s   $0.0039 .. $0.0054

32 created: 3 priced, 25 free, 4 not metered, 0 UNPRICED
```

**And the line worth reading twice:**

```text
where it accrued (low bound)
  apply:stage-apply      $0.0029
  outside any phase      $0.0154
```

Five sixths of a cycle's money is spent while no phase is running at all — the
environment is simply up. The plan asked for cost "per phase", which is not a
property a lifetime has; overlap attribution is what is well defined, and the
first thing it says is that the phases are not where the money is.

## Three inputs, three homes

```text
site/data/rates.json     CAPTURED. Five unit prices from the Price List Query
                         API, each with its SKU and the filters behind it
scripts/sizing.py        DERIVED from infra/. Nothing records the shape, so
                         nothing can go stale; it refuses if a .tfvars appears
assets/cost-model.json   EDITORIAL, like assets/topology-groups.json: which kind
                         is worth metering, and why the rest are not
```

`make rates-check` is the coverage half: every kind the per-cycle levels declare
is priced, free, or named as deliberately not metered — never zero by silence.
It reads the kinds out of `infra/`, so a NAT gateway added to the network module
reddens a gate instead of costing money invisibly. The fold has the matching
refusal from the other side, for a kind it OBSERVES and cannot price; on the real
cycle it reported 0 UNPRICED across 32 resources.

## What was broken on purpose

Thirteen deliberate defects, green controls either side, in the log. Eight in the
fold — the meter reading `elapsed_seconds`, the band collapsed to one end, the
ten-minute RDS minimum dropped, an unknown kind quietly counted free, a lost
orphan delete, an open meter reported closed, a GB-month price applied per hour —
and five refusals of the coverage gate.

**One did not test what it was aimed at.** Forcing `closed = True` to fake a
closed cycle made the fold dereference a destroy timeline that was not there, so
it crashed instead of producing a plausible wrong answer. Loud, but the
assertion never spoke. Re-run as a lie about `state` alone, it reddened two
cases. Same family as the break test that fails to break: the instrument has to
be aimed at the thing being claimed.

**And one gap the log names rather than hides.** Every coverage refusal except
the last was measured while the rate table was still missing, so each of those
runs carried two findings, and a run with two findings cannot prove the first one
fired for the reason claimed. The green control taken after the capture is what
closes it — and it is the only run in the whole file where `rates-check` has been
green.

## A prediction that was wrong again, and one that was right

`docs/session-primer.md` budgets one failed run for a genuinely new AWS path.
`aws pricing get-products` returned all five prices on the first attempt — the
sixth time running that prediction has missed. What it missed for: the price
list's `usagetype` encodes the region with an abbreviation no rule derives
(`USW2`), which is a refusal in `fetch-rates.py` rather than a guess, and the one
place this table is not portable to another region without a human.

The captured prices matched the figures estimated from memory before the capture,
to the digit. That is worth stating precisely because it is not evidence of
anything: a remembered price that happens to be right is still a remembered
price, and the reason the table is captured is that nobody can tell the two apart
by looking.

## Deliberately not done

```text
wiring      the fold runs by hand. Putting it in the destroy job means pairing
            that run with the apply that created what it is deleting; the rule
            (nodes-apply.json IS the environment's last apply, by construction)
            needs its own break test before it is trusted
the page    nothing renders yet. rates.json publishes with site/, so the data is
            in place when 20e wants it
the bill    ADR-0039 D3's one-off reconciliation is retired in ADR-0045 D6, not
            deferred: an estimate is what was asked for, Cost Explorer needs
            another credential and answers a day late, and Budgets already
            watches actual spend from the other side
```

## Validation

```bash
make cost-check     # 6/6 fixtures
make rates-check    # clean: 26 kinds, 3 priced, 19 free, 4 named
make docs-check     # 6 documents, 0 findings
make site-data-check
python3 scripts/fold-cost.py --environment stage --apply <apply> --destroy <destroy> --nodes <nodes-apply>
```
