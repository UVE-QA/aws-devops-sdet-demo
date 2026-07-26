# ADR-0019: Retire the Claude Project mirror; load state from git only

## Status
Accepted (Phase 9.0). Removes the manual-sync ritual introduced informally
around Phase 5 and encoded in phase-gates.md, discussion-log.md and
session-primer.md.

## Context

Two files were kept as READ-ONLY copies inside the Claude Project so that a chat
session with no access to the repository could still learn the project's state:

```text
discussion-log.md    the narrative: current phase, decisions, gotchas
project-prompt.md    the build prompt
```

Keeping them current was a manual step the user had to perform at every phase
gate, and `docs/phase-gates.md` required Claude to *remind* the user to do it in
every STOP summary.

`discussion-log.md` moved into git in `1f50243`.

**`project-prompt.md` had never been in git at all** — not in any commit, not
anywhere in history. The first version of this ADR asserted that both files were
tracked and reasoned from there. That assertion was written from memory and was
not checked against `git ls-files`.

It was caught at the moment of deletion. Acting on this ADR as originally
written would have removed the only copy of a 2,271-line document. The file was
committed first, in `96e110c`, and nothing was deleted until it was.

The decision below is unchanged, but it now rests on a different footing: the
Project holds no state **because everything it held is in git** — which had to
be MADE true, not observed to be true.

On 2026-07-25 the mirror was measured against the repository for the first time
in weeks. It was **five commits stale**, and it did not contain
`docs/session-primer.md` at all — the file the startup prompt names first. The
chat read it, found it untrustworthy, and loaded state from git instead. The
mirror cost a round trip and contributed nothing.

That outcome is structural rather than accidental. A manual sync is skipped
exactly when a session has been long and tiring, which is precisely when the
next session most needs accurate context. A duplicate whose freshness depends on
discipline will be stale in proportion to how much the project has been moving.

The mirror's only remaining value is a chat that can neither clone the
repository nor reach the devbox. Such a session cannot deliver a file or run a
command either, so it cannot do the work the context would be for.

## Decision

1. **The Claude Project holds no state.** The two mirror files are deleted from
   the Project. What remains there is the pointer already present in the
   Project's custom instructions, which carries no state and therefore cannot go
   stale — the same design as `docs/session-primer.md` itself.

2. **The manual-sync ritual is removed from the repository**: the
   "Manual sync reminder" section of `docs/phase-gates.md`, the
   "Manual Project-file sync" and "Project-file update workflow" bullets of
   `docs/discussion-log.md`. Claude must no longer ask the user to upload
   anything at a phase gate.

3. **The chat's fallback when the clone fails is the DEVBOX, not a mirror.**
   Ask for `git -C ~/aws-devops-sdet-demo log --oneline -5`, then for the
   contents of the files listed in section B of the primer, one at a time. This
   is slower than reading a prepared copy and it is never stale.

4. **A phase gate ends in git.** Update the cursor, write the session summary,
   commit, push. Nothing outside the repository has to be touched for the state
   to be correct.

## Correction, same day

The near-miss is recorded here rather than in a commit message because it is
evidence about this ADR's own reliability. The document argued that copies
outside git rot unnoticed, and was itself written on an unverified claim about
what git contained. The failure mode it describes does not spare documents that
describe it.

It also corrects the record from 2026-07-25 session 4, which stated that
everything unique in `~/Projects/aws-devops-sdet-demo` had been committed and
that the folder could be deleted. That was wrong by exactly one file — the one
that mattered most, because it existed nowhere else.

Operational rule taken from this: **a document is committed BEFORE the copy it
duplicates is removed, and "it is already in git" is checked with `git ls-files`,
never recalled.**

## Consequences

- One entire class of drift disappears. There is no second version of the
  project's narrative that can disagree with the first.
- The cold-start path costs a few extra round trips while the repository is
  private. It becomes free at Phase 11, when the repository goes public and the
  sandbox can clone without a token.
- Phase-gate closing gets shorter and has no step that depends on the user
  remembering to do something later.
- Anything genuinely worth carrying between sessions must now be written into
  the repository — which is where the project already claims its source of truth
  is. The mirror let that claim be false without anyone noticing.

## Alternatives rejected

**Keep the mirror, sync it more diligently.** The failure mode is not
carelessness; it is that the step is manual, unverifiable and comes last. The
same reasoning retired the "remember to validate prod" assumption earlier in
Phase 9.0: a check that depends on someone remembering is not a check.

**Automate the sync.** The Claude Project has no API for uploading files, so
this would mean a browser automation to keep a duplicate of something already in
git. Effort spent to preserve the problem.

**Keep only `project-prompt.md` in the Project.** It is also tracked in git, so
it has the same duplicate-and-drift shape. Its §14 is already superseded by
`docs/next-phases.md`, which makes a stale copy actively misleading.
