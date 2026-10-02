# ADR-0103: The application, drawn

## Status
Accepted (2026-10-02). Adds a second cut to `Details` beside **ADR-0079**'s
one; the first picture on the page that is drawn rather than derived.

## Context

The owner, after an explanation of what the api and the worker each do and
why the worker exists at all:

> давай сначала сделаем схему приложения с внутренними флоу чтобы было
> наглядно ... во вкладке детали

Every picture on the page until now is derived - the map from `infra/`, the
estate schema from the modules' inputs and `helm template` (ADR-0099), the
counts from the bucket - and held to its source by a gate. The application's
inside is not in any of those sources as a flow: the outbox, the two queues,
the receipt, the projection are code, and a flow through code is a reading of
it. A mock was drawn first and corrected twice on the owner's eye, not
committed until the owner chose: *давай пока первый вариант, svg в details,
но чтоб она открывалась по запросу а не постоянно портянка на весь экран*.

## Decision

**D1. Drawn, and the page says so.** One item followed through both services
in ten numbered steps - the request and the transaction that writes the item
with its event, the relay, the two queues, the receipt, the report, the
projection - with the dead-letter path and the credentials. The summary line
reads *drawn by hand from the code, not generated*. The facts were read from
the files `scripts/draw-app-flow.py` names, the day it was drawn; when one of
them changes, the script is edited and rerun.

**D2. In the page's own vocabulary.** The marks are `<use href="#ic-…">` into
the sprite `scripts/build-site-page.py` already inlines, so no icon is copied
twice and the picture is 9 KB; the colours are classes the template styles
with the theme's variables, so it follows light and dark with everything
else. `assets/app-flow.svg` is the drawing's one copy, injected at
`<!--APP-FLOW-->` by the page builder, and `site-page-check` refuses a page
that carries another. Wide, it scrolls inside its own box rather than
shrinking - ADR-0099's rule for the schema. The ten steps are an HTML list
under it, so they wrap on a narrow screen.

**D3. A second cut, closed by default.** ADR-0079 flattened every page-level
`<details>` but one, which earned it on size; this one earns it the same way
- the height of a screen, a reference rather than a reading - and on the
owner's word. When a derived picture replaces it, it goes the way the owner
named: under a cut, or expanding like the services do.

## Consequences

- The page has one picture no gate can hold to the code. That is said on the
  picture, and the script lists what to reread. A derived version - tables,
  queues and the receipt count from `services.json`, the models and the queue
  module - is the natural next step if this one earns its place.
- Found on the way, not caused by it: `measure-page`, a manual instrument and
  not in `assets/gates.json`, refuses on `main` too - its fixture lacks
  `/status/progress/lab.json`, which the page has asked for since the lab got
  a progress file.
