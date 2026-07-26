# ADR-0020: A chat session reads the repository over a read-only token and writes back as a patch

## Status
Accepted (Phase 9.1). Amends the workflow described in ADR-0019 and
`docs/session-primer.md` sections A and "Delivering files from a chat to the repo".
Expires by its own terms at Phase 11.

## Context

ADR-0019 retired the Claude Project mirror and made git the only source of
session state. It left the chat session with no way to reach git while the
repository is private, so `session-primer.md` §A prescribed a fallback: the user
pastes `git log`, then the contents of each state file, one at a time.

That fallback has two costs, and the second one is the expensive one.

**It is slow.** Four or five files pasted by hand before the session can say
what phase it is in.

**It reproduces the failure ADR-0019 exists to prevent.** What the session
reads is not the repository; it is a hand-selected excerpt of the repository,
chosen by whoever is doing the pasting. Nothing checks that the excerpt is
complete or current. On 2026-07-26 this was demonstrated cheaply: a clone left
in the session sandbox by the previous chat was four commits behind `origin/main`
and looked authoritative. It was caught only because the first act of the session
was to compare a hash — not because anything about the copy announced itself as
stale.

The output direction had a symmetric cost. Each authored file needed a `cp` into
`outbox/` and a `send.sh` invocation — roughly two commands per file, plus a
commit message decided per file rather than per change.

## Decision

**In: a fine-grained, read-only token, per session.**

The user creates a GitHub fine-grained personal access token scoped to
`UVE-QA/aws-devops-sdet-demo` alone, with `Contents: Read-only` and a short
expiry, and pastes it at the start of the session. The session clones over
HTTPS, immediately rewrites `origin` to the credential-free URL, and reads state
from that clone.

This is a deliberate, bounded exception to "never ask for secrets". It holds
because the token cannot write anything, cannot reach any other repository, and
expires on its own. The rule it bends exists to keep credentials that can cause
damage out of chat contexts; a read-only token on a repository that becomes
public at Phase 11 is not one of those.

**Out: one patch per session, not one command per file.**

Files authored in chat are committed inside the session's own clone, with real
commit messages, and exported as a single mbox patch via
`git format-patch <base>..HEAD --stdout`. The user transfers that one file and
applies it with `git am`.

`send.sh` and `outbox/` remain for one-off deliveries. They are no longer the
normal path.

## Consequences

- The session reads what `origin/main` actually contains, and the base of every
  patch is a real commit hash. A mismatch between the session's assumption and
  the devbox's reality makes `git am` fail loudly and change nothing — the same
  property the primer already asks for from patch scripts.
- Commit messages are authored with the change instead of at delivery time, so
  history stops being a sequence of "docs: add file".
- The token is a real credential in a chat transcript, with a real cost: it must
  be revoked by hand when the session's phase closes, not left to expire.
  Sessions do not share tokens; a token pasted in one chat is spent.
- `git am` requires a clean tree at the expected base on the devbox. That is a
  constraint, and it is the point: it refuses to apply onto a diverged working
  copy rather than merging blindly.
- **This ADR is temporary by construction.** At Phase 11 the repository goes
  public, the clone needs no credential, and the token half of this decision is
  superseded with nothing to replace it. The patch half stays.

## Rejected

- **Keep pasting file contents.** Rejected on the evidence above: it is not
  merely slower, it is a copy outside git wearing the clothes of the source of
  truth.
- **A write-scoped token so the session pushes directly.** Rejected. The rule
  that the chat never commits directly is what keeps a human between an authored
  file and `main`, and a write token would also be a credential worth stealing.
- **A deploy key or SSH.** Rejected: the sandbox has no outbound SSH.
