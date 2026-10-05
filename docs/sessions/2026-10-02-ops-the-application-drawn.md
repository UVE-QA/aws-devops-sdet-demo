# Ops — the application, drawn

**2026-10-02**, on `next`. **ADR-0103**.

## What the owner asked

After a list of what is queued, the owner asked again what the api and the
worker each do, and why not one backend. The answer was honest: the work the
worker does is trivial, and it exists to show the shape - a response that does
not wait for the work, failures isolated by a queue, separate releases, data
owned by each. Then *is it a Kafka analogue* - by role, not by structure: a
queue of tasks, each read once and deleted, against a retained log many
groups read and replay. Then the owner's summary, corrected twice: both
services write the database, each its own schema; and the worker does not
guard anything - the outbox, the queue's redelivery, the dead-letter queue and
the worker's idempotent receipt do, together.

> давай сначала сделаем схему приложения с внутренними флоу чтобы было
> наглядно

## What was drawn

A mock first, in the scratchpad: ten numbered steps, every fact read from the
code - the three tables of the api's schema and the worker's receipts, the
relay's `FOR UPDATE SKIP LOCKED`, the receipt's `on conflict do nothing`, the
event deleted only after the report. The first draft said five failed
receipts before the dead-letter queue; the module says three, and the draft
was corrected before anyone saw it. Two redraws for legibility - labels over
arrows, lines across titles, a step that read as part of a queue.

The owner chose the static picture in `Details`, closed until asked for. It is
drawn by `scripts/draw-app-flow.py` into `assets/app-flow.svg`, uses the
page's icon sprite and theme variables - light and dark both photographed -
and the page builder injects it, so `site-page-check` holds the copy. The ten
steps are an HTML list under it.

## The polling, made quiet

The page was metered in a browser over the live bucket: 23 documents every
30 seconds, all full `200`s, about 5 MB an hour per open tab whether visible
or not. Free, and still waste a reviewer's network panel would show. On the
owner's word the page now revalidates instead of re-downloading - CloudFront
answers `304` with no body - and stops polling in a hidden tab; metered again,
31 KB per three visible minutes instead of 255 and nothing while hidden, with
the same cadence and every page check green.

## #41

The owner pressed the button over the day's work. Green in 68 minutes:
signed in to ECR Public, three images on the first attempt; the first snapshot
in the bucket 25 seconds after the press, and the page - polling quietly now -
closing the button and drawing the cycle within the next half-minute, exactly
as fast as before; three `destroyed` after.

## What is still open

A derived version, if this one earns its place. `measure-page`'s fixture,
which lacks the lab's progress file on `main` too.
