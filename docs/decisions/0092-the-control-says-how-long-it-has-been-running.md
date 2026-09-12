# ADR-0092: The control says how long it has been running

## Status
Accepted (Phase 40, 2026-09-12). The pair to **ADR-0087**: that one says how long
a cycle takes, this one says how long this cycle has been going.

## Context

The elapsed clock lived in the `Current cycle` card, which is on `Now` and
nowhere else. A reader on `Estate` watching the board light up, or on `Cycle`
watching a phase pulse, could see THAT a cycle was running and not how far into
it they were — and the estimate that would make that number mean something is on
the control row, four parts away from it. The owner:

> после запуска цикла на кнопке показать сколько именно сайкл раннинг, те
> перенести из каррент сайкл в кнопку для видимости во всех вкладках

## Decision

**D1. The button carries the clock while it is closed.** `A cycle is running ·
5m 27s`, beside `≈ 52 min`, on every part. Two numbers that belong together and
were on different screens.

**D2. It ticks without a render.** The button holds its own `data-since` and a
one-second interval rewrites four characters, the same rule the map's phase
clocks and the open cost figure follow: `renderAll()` rebuilds the panel, and
doing that once a second would throw away the layout work sixty times a minute.

**D3. No run, no clock.** `busy` is also true for the three minutes after a press
before the run appears in a GitHub read (`launchedButNotYetSeen()`), and there
the button says what it always said. A clock with nothing behind it would be a
number this page made up, which is the one thing this page does not do.

**D4. The `Current cycle` card keeps its badge.** It is not a duplicate: the card
reports the RUN — `success · 52m 5s` when it is over, `waiting for review` when it
is held — and the button reports the CONTROL, which is closed or open. They agree
while a cycle runs because they are measuring the same thing in that minute.

## Consequences

- The control row now reads `A cycle is running · 8m 4s   ≈ 52 min   3 of 3`:
  what is happening, how long it takes, and how many are left. Three facts, one
  row, none of them written by hand.
- One more second-ticker in the dashboard script. It exits on its first line when
  the button is not saying a cycle is running, which is most of every day.
