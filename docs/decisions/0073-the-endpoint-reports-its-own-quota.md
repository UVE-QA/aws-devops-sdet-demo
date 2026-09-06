# ADR-0073: The endpoint reports its own quota

## Status
Accepted (Phase 37, 2026-09-06). Answers the objection recorded in the page's own
comment when the quota tile was built, and narrows nothing else. Applied.

## Context

The tile showing how many public launches the day has left derived its number by
counting workflow runs whose name carries an endpoint-issued id, on the calendar
day in the quota's zone. The comment beside it said why not to ask the endpoint:

> A GET would be authoritative and would also mint a nonce and a DynamoDB write on
> every page load, which is a worse trade for a figure that only has to be roughly
> right to stop a visitor pressing a button that will refuse.

Roughly right held until the counter was touched by hand. **ADR-0072**'s migration
deleted one day's counter; the run history it was derived from could not be
deleted, and the two sources parted:

```text
the counter   0 used, 3 available   — and it is what actually refuses
the page      3 used, 0 left        — and it disabled the button over it
```

The page was telling a visitor the button would refuse when it would not, and
disabling it so they could not find out. An approximation that is conservative in
the wrong direction is worse than one that is merely imprecise: it removes the
control rather than mislabelling it.

## Decision

### D1 — a status read that mints nothing

`GET ?quota` returns the day, the zone, the cap, launches used, launches left and
seconds to reset. It writes **nothing**: no nonce, no lock, no increment. The
objection above was to the write, not to the read, and it is answered rather than
accepted.

The kill switch is still checked first. A parked endpoint should not answer
questions about a quota nobody may spend — the same reasoning 19d applied to the
nonce path, where a switched-off endpoint went on handing out nonces.

### D2 — `read_day` is a read, and `decide_launch` still does not use one

The store interface gains `read_day`, used by the status path only. The cap
continues to be enforced by a conditional increment inside DynamoDB, because
read-then-write is how two simultaneous presses both see two and both become
three. A read added for reporting must not become the read the guardrail trusts.

### D3 — the page prefers the endpoint and keeps its own count as the fallback

The derived count still runs, and renders immediately, so the tile is never blank
waiting on a fetch. When the endpoint answers, its number replaces it. The
tooltip says which of the two produced what is on screen, because "3 of 3" from
two different sources is two different claims.

## Consequences

- One extra request per page load, answered from a single `get_item`. Against the
  60-per-hour anonymous GitHub budget this costs nothing — it is a different host.
- An endpoint that is refusing everything still answers `?quota`, unless the kill
  switch is on. That is deliberate: "why is the button gone" is exactly the
  question a visitor has then.
- **The disagreement that motivated this was self-inflicted**, by a one-off
  `delete-item` during ADR-0072's migration. The fix is worth having anyway: any
  future hand-edit of the counter, and any launch dispatched outside the page's
  view, would have produced the same split.
- Not done: the page does not re-read the quota on a timer, only at load and
  after a launch. A cycle another visitor starts will not move the tile until a
  reload. Named rather than solved, because the counter changes at most three
  times a day.
