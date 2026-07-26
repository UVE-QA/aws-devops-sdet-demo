# ADR-0022: Prod's approval gate requires a public repository, so Phase 11.0 moves ahead of the rest of 9.1

## Status
Accepted (Phase 9.1). Amends the sequencing in `docs/next-phases.md` and the
cost claim in ADR-0017 D1.

## Context

ADR-0017 chose a GitHub Environment with required reviewers as prod's approval
gate, and described it as "free and built in". The first half was wrong for this
repository.

GitHub's documented limits: environments, environment secrets and deployment
branches in **private** repositories require Pro, Team or Enterprise; the
protection rules themselves — required reviewers and wait timer — are available
on Free, Pro and Team **only for public repositories**. Required reviewers on a
private repository means Enterprise.

Observed directly rather than inferred: on the `prod` environment page of the
private repository, the *Deployment protection rules* block was not rendered at
all. The page began with *Deployment branches and tags*.

The consequence is specific, and worse than "a feature is missing".
`environment: prod` in a workflow still works without protection rules — the
environment is created implicitly and the OIDC token carries the
`environment:prod` subject, so the deploy role built in ADR-0021 is assumable.
Everything would have *worked*. The only thing absent would have been the stop.

That is precisely the failure this project keeps finding in its own work: a
control that reports success and enforces nothing. ADR-0021 had just finished
removing the branch subject from prod's trust policy so that the environment
would be the only path in — and the environment would have had no lock on it.

## Decision

**Publish the repository now**, as a step `11.0` pulled out of Phase 11 and
placed ahead of the remainder of 9.1. The repository was going public at Phase
11 regardless; moving it earlier costs nothing that was not already planned and
turns the gate from decorative into real.

The rest of Phase 11 — the public dashboard on S3 + CloudFront — stays where it
is. Only the visibility flip moves.

Rejected alternatives:

- **A temporary `workflow_dispatch` gate** requiring the operator to type
  `PROMOTE`, mirroring `destroy.yml`'s `DESTROY`. Rejected: it is a second gate
  that looks finished, in a project whose recurring defect is exactly that. It
  would also have to be removed later, and removals get forgotten.
- **Leaving prod ungated until Phase 11.** Rejected: 9.1's closing criterion is
  a `stage → approve → prod` cycle. Without the approve there is no cycle to
  close, only a claim.
- **Paying for Enterprise.** Rejected on cost for a demo project.

## Consequences

- The approval gate is real: prod's role trusts `environment:prod` and nothing
  else (ADR-0021), and that environment now carries required reviewers.
  Both halves exist, in two different systems, and neither is sufficient alone.
- The read-only clone token of ADR-0020 becomes unnecessary immediately. Its
  expiry condition was written into that ADR and has now been met; verified by
  an anonymous clone of `a1c4402` with no credential present.
- GitHub Actions minutes are free on public repositories, which removes a
  budget concern that was never large but was real.
- The repository is readable by anyone from this point. What that exposes, and
  why it was accepted rather than rewritten, is ADR-0023.
- `docs/next-phases.md` Phase 11 now reads "dashboard" only; the visibility flip
  is recorded as done here and in `docs/phase-gates.md`.
