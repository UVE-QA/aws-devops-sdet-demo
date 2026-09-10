# Phase 39 — What four cycles and a pair of eyes found

**2026-09-08 → 2026-09-10**, one session across three days.
**ADR-0075** … **ADR-0085**, eleven records.

The subject was supposed to be a visual: make the estate board light up as a
cycle builds it. It became something else. **Every defect below was found by
running a cycle or by the owner looking at the page. `make gates` was green
through all of them,** and three of the gates were themselves red or blind
before the session started.

## The cycles

```text
#14  2026-09-08  failure   promote: ALB stuck 10m in `provisioning` — AWS, not us
#15  2026-09-09  success   first clean cycle with the live progress feed
#16  2026-09-09  success   verification of the derived job names
#17  2026-09-10  success   verification of the phase-span merge
```

Cost: four cycles, each ≈ $0.09 by the page's own fold. Nothing left behind —
`OK: no billable resources remain` on every teardown, both environments
`destroyed`, both progress documents removed.

## What the live cycles found

**The bar was lying on every cycle, not the first (ADR-0077 D3).** ADR-0076 D4
called it a count and not a forecast, which was right about forecasts and wrong
about the count. Watched at 17:12 on 2026-09-08:

```text
17:12:13   stage.vpc  incomplete  4 of 7
17:12:29   stage.vpc  measured    9 of 9
```

`resources_observed` counts what has **started**, not what there is, so the
denominator grows and a bar against it stands at 100% on an unfinished node.
The map's own `resources` is no better — it counts resource *blocks*, and
`count`/`for_each` turn six into nine at apply time. Nothing knows the total
until the apply is over, which is what *being created* means. The bar is
indeterminate now and the sentence lost its denominator.

**The stop step ran under the wrong role (ADR-0077 D7).** `##[warning]could not
remove the progress document`, printed in yellow, job green. The step sat before
the swap to the publish role, so `aws s3 rm` ran under the deploy role. The
document stayed in the bucket describing an environment minutes from teardown —
and did no harm only because a *different* defence held, the record superseding a
partial reading four seconds later.

**Then #14 failed and took out both defences at once (ADR-0076 D8).** prod's
apply timed out on an ALB, so no record was published to supersede with, and the
removal was denied for the reason above. The page went on drawing a prod that was
being torn down as it read. A partial reading has a shelf life now — two minutes,
eight missed writes — and that is a fact the *document* carries, so it holds when
the bucket, the workflow and the credential have all failed together.

**stage was never priced, and prod always was (ADR-0080 D1).**

```text
destroy       no cost to publish (looked at: '<none>')
destroy-prod  cost: prod — COMPUTED ESTIMATE, 3 priced, 27 free
```

`destroy-prod` *calls* `destroy.yml`; self-service's own `destroy` job was a
hand-written copy of it — sixteen steps against nineteen — missing exactly one:
`Price the cycle from its two timelines`. Every cycle the button has ever run
priced prod and never priced stage. It calls now; 176 lines of copy gone.

**And the prod half of the map had never pulsed on the public path (ADR-0080 D2).**
Found while fixing the above: `site-data-check` went red because the phase named
steps the caller no longer had, and reading the binding table showed
`promote-prod.yml::promote` and `destroy.yml::destroy` — workflows that are not
the one running. A button cycle's run *is* `self-service.yml`, so four phases had
matched nothing since ADR-0068 and sat at `not reached yet` for entire cycles.

A called job is named twice: `destroy` in the file, `destroy / destroy` in the
API. Writing the runtime name by hand was tried and the generator **refused it**,
correctly. The groups file keeps the file's name and the generator derives the
other.

**Both teardown tiles lit for eighteen minutes (ADR-0081).** The page's own
comment predicted it — *when the run does not say which environment it is about,
both are lit* — and that premise is false on a path where the two teardowns are
two differently-named jobs. Verified frame by frame on #17: `stage` dark at
01:36, `prod` lit at 01:44, through the five-minute hold.

**Phase 8 published two spans under one key (ADR-0083).** 468s from stage and
469s from prod, folded by the same id, last write wins — which is the order of
the `ENVS` array and nothing else. Beside it the live clock read eighteen
minutes. Merged when both documents name the same run, and #17 confirmed it:

```text
stage  04:05:43 → 04:13:21 = 458 s
prod   04:20:17 → 04:28:09 = 472 s
union  04:05:43 → 04:28:09 = 1346 s = 22m 26s   ← what the page now draws
```

## What the owner's eyes found

Every layout change in this session came from him looking at a screenshot, and
the diagnosis was his more often than mine.

- *«вот это в детали»*, *«растяни плашки»*, *«все значки одинаково большие»* —
  three separate width and size faults I had fixed locally instead of seeing as
  one system.
- **«дело в позиции, а не в весе»** — I made the permanent levels big, he said no,
  I made them small, he said no again: the problem was where they sat. I had the
  diagnosis wrong twice.
- **The live/static sort.** I cut the page by *subject* — Now, Estate, Cycle,
  Tests — which is a table of contents. He re-cut it by *does a cycle change it*,
  which is a property of the data, in one message.
- **«названия чего?»** A slug is an identifier, not a statement.
  `aws-devops-sdet-demo` made the row look like ADR-0082 D3's cost had been paid
  while leaving it exactly where it was.

## Three gates were red or blind before this started

- **CI had failed on every push since 2026-09-06** at `page-freshness-check`, and
  `suite-inventory-check` was *skipped* behind it — so main carried two red gates
  and only one was visible. A skipped step reads like a step with nothing to say.
  Both were ADR-0073's quota fetch and a test renamed two phases earlier.
- `check-action-pins.py` read only `.github/workflows/` and would have been green
  over the first unpinned action in the composite added this session.
- `check-publish-prefixes.py` named one publisher by hand — the exact defect
  ADR-0044 was written to prevent, sitting in the checker written to prevent it.

`make gates-full` exists now: the same list, asked what *this machine* can
answer, probing rather than believing. 22 of 32 on the devbox against 12.

## And one gate paid for itself immediately

`claim-chain` (ADR-0085) compares the pipeline's verb chain in the README, in the
page's claim and in the row beside the name. **Its first run found the row had
dropped `approve`** — the only step in the chain that involves a person, drawn by
the map as a phase of its own — an hour after I wrote it.

## Left named and not done

- `Details` holds the request path; `Cycle` is arguably where it belongs. An
  exception to ADR-0079's sort needs a better reason than a hunch.
- The `Cycle` part is the tallest at 1.1–1.7 screens and is bounded by the map,
  not by the parts.
- Nothing checks that a `data-part` value is one of the five, or that a live
  binding ever matched a real job.
- The phone: 2.2–4.4 screens per part, and a 105px overflow on `Tests` from the
  run-history table. Deferred by the owner.
- The undiagnosed release-tag 403 of 2026-09-05 is still undiagnosed.
