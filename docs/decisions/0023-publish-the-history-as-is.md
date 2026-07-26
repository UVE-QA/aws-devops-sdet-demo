# ADR-0023: The repository is published with its history unrewritten

## Status
Accepted (Phase 9.1). Prerequisite of ADR-0022.

## Context

Before making the repository public, all 53 commits were swept.

The sweep was manual pattern-matching over `git log -p --all`, not `gitleaks`.
`docs/next-phases.md` 11.0 asked for gitleaks over the full history; that is
still owed, and Phase 15 puts it in CI. What follows is therefore evidence, not
a proof of absence.

**Clean on secrets.** No AWS access keys, no private keys, no API tokens, no
certificates, in any commit. No `.tfvars`, `.tfstate` or `.env` file was ever
committed — `.gitignore` covered them from the first commit. The only
password-shaped string is `POSTGRES_PASSWORD=demo` in `docker-compose.yml` and
`.env.example`, which is the local Compose database and never leaves a laptop.

**Not clean on identifiers.** Three things become permanently public:

```text
993912191738                  AWS account id, 13 files, including every backend.tf
34.213.147.86                 devbox static IP (and private 172.26.4.52), 2 files
papers.usher.3m@icloud.com    3 places in docs — and the author of 52 commits
d-90661cc65d.awsapps.com      IAM Identity Center start URL, 2 files
```

The fourth line was found **after** the sweep had already been reported as
complete, while updating `next-phases.md` — whose own 11.0 checklist had named
the SSO start URL as a thing to decide about, and which the sweep had not read
before running. The sweep was pattern-matching for credentials; it was not
driven by the checklist that already existed for this exact step. Recorded
because the near-miss is the point: the list of what to look for was written
down, in this repository, and was not consulted.

Removing any of them means rewriting history with `git filter-repo`, which was
still cheap: no forks, no external clones, one working copy.

The measurement that decided it:

```text
39 real commit hashes are referenced in docs/, 103 times.
```

This project documents by hash. ADRs and session summaries are built on
sentences like "fixed in `b71b846`" and "closed at `e1e577a`". A rewrite changes
every hash, and all 103 references become silently wrong — pointing at nothing,
with no error to announce it.

That is the same failure mode as the retired Project mirror (ADR-0019) and the
`project-prompt.md` near-miss: a document that confidently describes a state
which does not exist. Trading a 52-commit author email for 103 broken references
buys privacy with the project's own core invariant.

## Decision

Publish as is. Do not rewrite history.

The exposed identifiers are accepted, each for a stated reason:

- **AWS account id** — not a secret by AWS's own model, and unavoidable in
  `backend.tf` and the state bucket name. There are no static credentials
  anywhere to pair it with: human access is SSO, machine access is OIDC
  (ADR-0002, ADR-0003). Knowing the number grants nothing.
- **Devbox IP** — a live SSH host, so this was checked rather than assumed:
  `passwordauthentication no`, `pubkeyauthentication yes`,
  `kbdinteractiveauthentication no`, root key-only. Key-only SSH is not
  meaningfully weakened by a known address; obscurity was never the control.
- **Email** — it is already the git author of 52 commits and a portfolio
  repository has an identifiable human behind it by design.
- **SSO start URL** — a login portal, not a credential; equivalent to knowing a
  company's identity-provider address. It grants nothing without a valid user,
  and MFA on the Identity Center user is what actually protects it. Confirm MFA
  is enforced; that is the control, and it is worth checking rather than
  assuming.

## Consequences

- Commit hashes stay valid, so every ADR and session summary keeps pointing at
  what it claims to point at.
- The three identifiers are public permanently. Rewriting later is possible but
  gets more expensive with every clone and fork, and the hash cost only grows.
- Four commits (`c62a3b8`..`a1c4402`) carry the author
  `Chat session (Phase 9.1) <claude@session.local>`, an identity the chat picked
  in its sandbox without being asked. It stays, for the same hash reason.
  Future sessions set the repository's own identity before committing.
- The devbox's Lightsail firewall should still narrow SSH to a source range.
  That is hardening, not a precondition, and is not blocking.
