# ADR-0055: Phases are numbered, and a phase carries the condition that closes it

## Status
Accepted (Phase 21, 2026-08-10). Applies from Phase 21 onward. Does not
renumber anything before it. Adjacent to **ADR-0033**, which made session entry
and exit commands; this is about the unit those commands open and close.

## Context

Phase 20 ran to thirteen entries: 20.0, then 20a through 20m.

The lettered sub-phase was meant to mean one session. It never did. 20a took
three sessions, 19g took two, and `docs/session-primer.md` already says so in
its naming rule — which exists precisely because a sub-phase title does not
change while several sessions run under it.

So the letters were a symptom. The cause is that **Phase 20's title has no
condition of completion.** "The cycle, visible without a log" is a direction,
and everything dashboard-shaped is on it. There was no sentence anywhere whose
truth would have ended the phase, so nothing ended it, and the alphabet absorbed
the difference.

This is the same shape as the failure ADR-0033 was written for: Phase 16b was
closed four times, each time reported complete. A unit of work with no
checkable end gets closed by feel.

## Decision

### D1 — Plain integers, from 21

No letters, no `.0`. The next phases are 21, 22, 23.

### D2 — A phase is created together with the sentence that closes it

When a phase is written into `docs/next-phases.md` it carries a **closing
condition**: a checkable statement, not a title and not a list of intentions.
Phase 22's is written there; so is Phase 23's.

A phase whose closing condition cannot be stated is not a phase yet. It is a
direction, and the first piece of work under it is to find the condition —
which is what a decisions session is for, and what Phase 21 was.

### D3 — History is not renumbered

Sessions before this ADR keep their identifiers. They are in the filenames under
`docs/sessions/`, in every row of `docs/sessions/INDEX.md`, in the cursor and in
the ADRs that cite them. Renaming them would break every reference in order to
tidy one table.

### D4 — More than one session per phase stays normal

Nothing about a number implies a session. A phase takes as many as it takes, and
the sessions are told apart the way `docs/session-primer.md` already says: by
the cursor's **Next allowed step**, which the previous session wrote there for
this purpose. The primer's `Phase <N>[.<sub>]` form still matches, because the
sub-part was always optional.

## Consequences

- `docs/phase-gates.md` gains rows without letters. The lettered rows above stay
  exactly as they are.
- Every new phase costs one extra sentence at the moment it is planned, and that
  sentence is the thing that lets `make session-close` be believed.
- This ADR cannot be enforced by a command. The closing condition lives in prose,
  and whether it is checkable is a judgement — the same category as whether a
  session summary is honest as opposed to present, which
  `docs/session-primer.md` already flags as what `session-close` cannot see.
  Deliberately not turned into a gate: a gate that has to ask rather than verify
  is a gate that cannot fail, and this repository has a rule about those.
- No tooling changes. Nothing parses a phase identifier.
