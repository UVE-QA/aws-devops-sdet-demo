# ADR-0072: The quota day is one named zone

## Status
Accepted (Phase 37, 2026-09-06). Reverses the reasoning in `utc_day()` and in
the unit test that asserted it. Applied to `infra/self-service`.

## Context

The daily cap was keyed by UTC date, and the docstring gave the reason:

> The counter is keyed by UTC date, so the reset time is the same everywhere.

True, and the thing it made the same for everyone was **17:00 in the afternoon**.
The owner watched the quota read `3 of 3` at 18:14 local, hours after spending
all three launches, because the UTC day had already turned. The window resets in
the middle of the working day, which is exactly when somebody is using it.

## Decision

### D1 — one named zone, and not the visitor's

`America/Los_Angeles`, configured as `var.quota_timezone`.

**Not the visitor's local time.** The counter is a single shared DynamoDB item.
A reset that followed whoever happened to be looking would empty at a different
moment for each of them — which is not less confusing than UTC, it is the same
confusion multiplied by the number of readers. One zone, named, and every reader
gets the same answer about when it resets even though for most of them that
answer is not their own midnight.

### D2 — named, never an offset

`America/Los_Angeles` is UTC−7 in summer and UTC−8 in winter. A reset pinned to
an hour of UTC would be an hour wrong for half the year, in the direction nobody
checks because nobody re-reads a working counter in December.

`seconds_until_quota_reset()` adds a day and truncates **in local time** rather
than adding 86400: across a DST boundary the local day is 23 or 25 hours long,
and the arithmetic that ignores that is right for 363 days a year.

### D3 — a missing tz database refuses

Python's `zoneinfo` needs the IANA data present. A fallback to UTC would move the
reset by seven hours while every message went on naming the zone — a counter that
lies about its own window is worse than one that stops. `quota_zone()` raises
`StoreUnavailable`, which the endpoint already turns into a refusal.

### D4 — the page counts the same day

`selfServiceRunsToday()` used `toISOString().slice(0,10)`, the UTC date. Two
definitions of "today" seven hours apart would put the tile and the endpoint into
open disagreement for seven hours of every day — and the tile says out loud that
the endpoint keeps the authoritative count, which is only worth saying while the
two usually agree.

The browser falls back to UTC if it lacks the zone. The tooltip already names its
source, and the endpoint is what actually refuses.

## Consequences

- **The window moved and three launches moved with it.** Under UTC keying the
  three public launches of 2026-09-05 had already reset by 17:00 local. Under
  local keying they belong to a day that had not ended, so the quota would have
  read `0 of 3` for another five hours. The owner chose to keep `3 of 3`, so
  `count#2026-09-05` was deleted once, by hand: those launches were counted under
  a scheme that no longer exists, and charging them to a window about to close
  buys nothing. A one-off, recorded here rather than left as an unexplained gap
  in the counter's history.
- The refusal message now names the zone and the local instant instead of
  `00:00 UTC`, so a visitor who is refused can tell when to come back without
  converting anything.
- `var.daily_cap`'s description said "a UTC day". Corrected in the same commit —
  it is the sentence somebody would have trusted next.
- The unit test asserting the old rule is rewritten, and it now uses a moment
  where the two zones DISAGREE. The old `NOW` is mid-morning local, where UTC and
  local dates are the same, so a test using only it would have passed against
  either implementation. Both sides of the DST boundary are asserted, and so is
  the refusal on an unloadable zone.
- Three Lambdas were repackaged for a change that only the launch function reads.
  They share one deployment package; splitting it is not worth doing for this.
