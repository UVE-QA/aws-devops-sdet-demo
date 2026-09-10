# ADR-0084: A slug is not a statement

## Status
Accepted (Phase 39, 2026-09-10). Pays back the cost **ADR-0082 D3** named when it
moved the identity bar into `Details`.

## Context

ADR-0082 D3 took the identity bar off the always-visible strip because it cost
145px on every part, and wrote the cost down: *the page no longer says what it is
above the fold*.

The first repair put the repository name back, left of the parts. The owner's
answer to it was one question:

> названия чего?

**A slug is an identifier, not a statement.** `aws-devops-sdet-demo` ties the
page to the link in a CV and tells a first-time reader nothing about what they
are looking at. It made the row look like the cost had been paid while leaving it
exactly where it was.

## Decision

**D1. The name carries one clause of the claim beside it.** The shortest true one,
taken from the paragraph that stays in `Details` rather than written fresh:

    aws-devops-sdet-demo   deploy → test → promote → destroy on AWS, reporting on itself

The name is bold — it is what the thing is called. The clause is muted — it is
what the thing is. Not a second copy of the argument: the paragraph, the links
and the decision-record count are still in `Details`, because knowing *where you
are* does not need them.

**D2. No live badge on the row.** `dashboard live` was in the first repair and is
a claim the page already makes better: two clocks, in `Now`, saying when each
half was last confirmed. A badge that says `live` next to figures that say *when*
is the weaker of two statements about the same thing.

**D3. It costs no height.** The row existed for the parts and the control; the
name went into it. Every part measures what it measured before ADR-0084 — 1.0,
1.0, 1.1, 1.0, 1.1 screens at 2560.

## Consequences

**The row wraps to two lines below 1366px**, measured:

    1512   55px, one line
    1440   55px, one line
    1366   55px, one line
    1280  107px, two lines
    1180  107px, two lines

That is 52px on a window narrower than the page's own `--page` cap, and it wraps
rather than overflowing. The clause could be shortened to move the threshold —
`pipeline on AWS that reports on itself` reaches about 1200 — and it is not,
because the longer one names the five verbs the whole page is about.

**This is the third statement of the same fact on one page**: the row's clause,
the paragraph in `Details`, and the README's opening that both come from. They
agree today because two of them were copied from the third. Nothing checks that
they still agree, and a fourth copy would be one too many.
