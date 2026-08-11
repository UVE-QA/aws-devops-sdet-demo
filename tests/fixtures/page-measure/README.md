# Fixtures for `scripts/measure-page.mjs`

The dashboard reads FOUR sources the sandbox cannot reach: the GitHub Actions
API, the two `status/*.json` files in the public bucket, the self-service
endpoint, and the run layer. A page measured with those sources unreachable is
not the page a visitor gets — discovery said so itself, in ADR-0047: "with three
remote sources unreachable — so the figures understate the live page".

It said *three*, and so did this directory, for two phases. The fourth was found
in Phase 25 by building a fixture for a different gate (**ADR-0059 D5**), and it
is the one that mattered most: without it every node on the measured page reads
`not run yet` and not a single figure is printed. See `layer/` below.

So the measurement freezes them. Two sets, because the page has two shapes and
the tall one is the one a layout has to survive:

```text
at-rest     nothing running, both environments destroyed. This is the page most
            of the time, and both status files here are REAL - captured from
            https://demo.uveapp.net/status/{stage,prod}.json on 2026-08-09.
in-flight   a deploy running with its steps, stage stale against a newer run,
            prod up with a load balancer, an image digest and a report link.
            Synthetic, and the tallest honest shape of every panel.
```

`meta.now` pins the clock (`page.clock.setFixedTime`), so `12 min ago` stays
`12 min ago` in a year and two measurements taken six months apart are
comparable. Without it every age string drifts and the widths drift with them.

What is real and what is not is recorded per file in `meta.provenance`. The
`in-flight` run ids and numbers are invented; the `at-rest` ones are the ids
the real status files name, so the staleness join in the page resolves exactly
as it does live.

These are frozen on purpose, exactly as `tests/fixtures/live-state/` freezes its
phases: the subject under measurement is the LAYOUT. If these tracked the live
account, a teardown would change the page height and the person who ran the
teardown would learn that the instrument moves on its own.

## `layer/` — the run layer, and why there is only one copy of it

The ten documents a cycle publishes into the bucket beside the page. They are
served over the top of `site/`, at the same paths, exactly as
`scripts/check-page-inflight.mjs` serves its own copy:

```text
timeline/<env>/nodes-apply.json     node figures from the last apply
timeline/<env>/nodes-destroy.json   ... and from the last destroy
timeline/<env>/latest.json          the last run, whatever happened
results/<env>/latest.json           what the suites said
cost/<env>/latest.json              what the cycle cost
```

**REAL, and unmodified.** Captured on 2026-08-11 from
`https://demo.uveapp.net/<path>`, byte for byte. They are the cycle Phase 20m
ran on 2026-08-09 — `deploy-stage #32`, `promote-prod #11`, `destroy #45` and
`destroy #44` — which is why the page draws `stage $0.0529 .. $0.0584` and
`prod $0.0182 .. $0.0237`, the two prices that session recorded in the cursor.

**One copy for both sets, and that is a consequence rather than a convenience:**
`at-rest` and `in-flight` declare the same `meta.now`, so a second copy would be
the same documents under the same clock. The two sets differ in what the Actions
API and the bucket say, which is what makes one of them tall.

The layer's own cycle is *later* than `meta.now` — 2026-08-09T21:58Z against a
clock pinned at 04:00Z the same day — and nothing on the page turns that into an
age. The figures are durations, the cycle carries a DATE and not an age, and the
only `… ago` strings on the page come from `runs.json` and the status files.
Checked by reading the rendered page rather than by reasoning about it, which is
the reason these documents are here unshifted instead of moved back a day to
make the ordering tidy.

**An origin 404 is a refusal, and so is a document that does not parse.** The
page's own reader is `r.ok ? r.json() : null` with a `.catch(() => null)`, so
both failures render as a shorter, quieter page with no banner — the empty
result that looks clean. `measure-page.mjs` parses every file in here before it
starts the browser, and refuses on any request its own server could not answer.
