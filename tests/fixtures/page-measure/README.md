# Fixtures for `scripts/measure-page.mjs`

The dashboard reads three sources the sandbox cannot reach: the GitHub Actions
API, the two `status/*.json` files in the public bucket, and the self-service
endpoint. A page measured with those sources unreachable is not the page a
visitor gets — discovery said so itself, in ADR-0047: "with three remote sources
unreachable — so the figures understate the live page".

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
