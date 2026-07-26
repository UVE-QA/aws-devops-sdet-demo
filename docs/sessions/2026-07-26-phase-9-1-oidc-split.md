# Session 2026-07-26 — Phase 9.1: the OIDC split, and the repository goes public

- Phase: 9.1 (build out prod). In progress, not closed. Phase 11.0 (publish the
  repository) was pulled forward and closed inside this session.
- Request: begin 9.1 with the second deploy role, and reduce the manual
  copy-paste the delivery workflow demanded.
- Tooling: Cowork chat on the MacBook driving, devbox executing. **State was
  loaded by cloning the repository into the chat sandbox over a read-only
  token, and delivered back as a single mbox patch** — the change ADR-0020
  records, adopted mid-session and used for its own delivery.
- **No AWS API was called and nothing was applied.** Zero cost.

## Result

```text
a1c4402  infra: one OIDC provider, one deploy role per environment
47c205c  ADR-0021: split the provider from the role; prod trusts no branch
dbd6a1b  primer: token-based state loading, patch-based delivery
c62a3b8  ADR-0020: read-only token in, one patch out
```

`terraform fmt -recursive -check infra` clean; `make tf-validate` OK on all five
root levels (`bootstrap`, `bootstrap-oidc`, `envs/prod`, `envs/stage`,
`shared-ecr`). Nothing applied.

## Finding 1 — the module could not have been instantiated twice

`infra/bootstrap-oidc` called one module, `iam_github_oidc`, that created the
OIDC identity provider **and** the deploy role. Phase 9.1 needs a second deploy
role for prod, and copying the module block would not have produced one: AWS
allows exactly one OIDC provider per issuer URL per account, so the second
instance dies on `EntityAlreadyExists`.

This is the project's standing failure mode, not a new one. The module was
correct on every path ever exercised and wrong on the first path never run —
the same shape as ADR-0015, ADR-0016 and the four Phase 9.0 defects. It was
found by reading the resource, before any apply, which is the cheapest place
this class of bug has ever been caught here.

## Finding 2 — the approval gate would have existed only in the UI

ADR-0017 makes prod's gate a GitHub Environment with required reviewers. The
existing trust policy grants `repo:<owner>/<repo>:ref:refs/heads/main`, and a
subject of that form is satisfied by **any** workflow running on `main`.

Had prod's role been created from the same template, an unreviewed workflow on
the default branch could have assumed it and applied to prod. The reviewers
would have been real in the GitHub settings page and absent from IAM — a gate
that reports success and stops nothing.

The role module therefore gained `trust_branch_ref`. Stage keeps `true`; prod
sets `false`, leaving `environment:prod` as its only subject. One boolean is the
whole of the AWS-side enforcement, which is worth knowing when reading it.

## What was built

```text
modules/iam_github_oidc_provider   the provider. One per account.
modules/iam_github_deploy_role     role + policy. One per environment,
                                   takes oidc_provider_arn as input.
bootstrap-oidc                     oidc_provider + deploy_role_stage
                                   + deploy_role_prod, plus three moved blocks.
```

Every resource-scoped statement in the role policy derives from `name_prefix`,
so the stage role grants nothing over prod resources and vice versa. That was
already true; instantiating the module twice is what makes it load-bearing.

An empty trust-subject list is now rejected by a `precondition` rather than
producing a trust policy nothing can satisfy — that failure would otherwise
surface as an opaque STS error at the next login, far from its cause.

`bootstrap-oidc` lost its `name_prefix` variable. Prefixes derive from the same
project literal the environments hardcode, so the alignment the old default
silently depended on is structural rather than conventional.

Also removed: the `github_*` entries in `infra/envs/prod/terraform.tfvars.example`,
dead since 9.0 deleted the module that consumed them.

## Decision — ADR-0020: how a chat session exchanges state with the repository

The primer's fallback for a private repository was "the user pastes `git log`,
then each state file in turn". Its real cost was not the typing.

**What it loads is a hand-picked excerpt of the repository, and nothing checks
that the excerpt is complete** — the exact failure ADR-0019 retired the Project
mirror to prevent, reintroduced as a procedure.

It was demonstrated cheaply at the start of this session. A clone left in the
sandbox by the previous chat was **four commits behind `origin/main`** and
looked entirely authoritative: right remote, clean tree, plausible HEAD. It was
caught only because the first act of the session was to compare a hash.

So: in over a fine-grained, read-only, single-repository token, with `origin`
rewritten credential-free immediately; out as one `git format-patch` mbox
applied with `git am`. The token half expires at Phase 11 when the repository
goes public. The patch half is permanent.

`git am` earns its place by refusing: it will not apply onto a diverged or dirty
tree, and changes nothing when it refuses. That is the property the primer
already demanded of patch scripts, applied to delivery itself.

The patch was self-tested before delivery — applied onto a clean checkout of the
base commit in the sandbox, and the resulting tree diffed against the authored
one. Faithful.

## Cost of the workflow change, measured

```text
before   ~2 commands per authored file (cp into outbox, send.sh), plus a
         commit message chosen at delivery time rather than with the change
after    1 command for the whole session: scp + git am + fmt + validate,
         chained on &&, every link failing loudly
```

The chat also mounted `~/Projects/_claude-transfer` directly, so it now writes
into `outbox/` itself and the "the chat must tell you its sandbox path" dance
disappears. The primer section that described that dance was updated.

## The gate did not exist

Setting up the GitHub Environment revealed the second half of the story. On the
`prod` environment page the **Deployment protection rules** block was not
rendered at all — required reviewers need a public repository outside
Enterprise, and this repository was private.

What made it urgent rather than annoying: `environment: prod` works fine without
protection rules. The environment is created implicitly, the OIDC token carries
the `environment:prod` subject, and the role built an hour earlier would have
been assumable. Everything would have worked. **The only missing piece would
have been the stop** — and ADR-0021 had just removed prod's branch subject
specifically so the environment would be the only way in.

A door with no lock, installed the same afternoon the key was cut.

So Phase 11.0 was pulled forward (ADR-0022) and the repository published. The
alternatives were a `workflow_dispatch` gate typing `PROMOTE` — a second thing
that looks finished, in a project whose recurring defect is exactly that — or
leaving prod ungated, which makes 9.1's closing criterion unmeetable.

## What publication exposed, and the number that decided it

The full history was swept before the flip: 53 commits, clean on credentials —
no keys, no tokens, no `.tfvars`, `.tfstate` or `.env` in any commit.

Four identifiers become permanently public: the AWS account id, the devbox
static IP, the owner's email (also the author of 52 commits), and the SSO start
URL. Removing any of them meant `git filter-repo`, still cheap with no forks and
one working copy.

```text
39 real commit hashes are referenced in docs/, 103 times.
```

This project documents by hash. A rewrite makes all 103 references silently
wrong — the same failure as the retired Project mirror and the
`project-prompt.md` near-miss. Published as is (ADR-0023), each identifier
accepted for a stated reason, and the devbox checked rather than assumed:
password authentication off, key-only.

**The sweep missed one.** The SSO start URL was found afterwards, while editing
`next-phases.md` — whose own 11.0 checklist had named it, along with the account
id and the IP, as things to decide about consciously. The checklist existed, in
this repository, and the sweep had not read it before running. Nothing was
harmed, because the decision would have been the same. The lesson is not about
the URL: **the list of what to look for was already written down and was not
consulted.** The sweep was also manual pattern-matching, not the gitleaks run
11.0 asked for; that remains owed.

## Open

- **Required reviewers on the `prod` environment** were enabled the same day:
  2 protection rules, administrator bypass off, `main` the only deployment
  branch. `Prevent self-review` is off by necessity — the only reviewer is the
  account that triggers the run, so enabling it would deadlock promotion
  entirely. In a solo project the gate is a deliberate pause, not separation of
  duties; that arrives with a second reviewer. This is UI state and git cannot
  assert it, so it stays on this list as something to re-check rather than
  assume.
- **gitleaks over the full history** is still owed; the pre-publication sweep was
  manual. Phase 15 puts it in CI, which is now late rather than early.
- **MFA on the Identity Center user** should be confirmed, not assumed: the SSO
  start URL is public and MFA is what actually protects the portal.
- The next local apply of `bootstrap-oidc` under `demo-admin` **must plan as 1
  role + 1 role policy added, 0 destroyed.** Anything else means a `moved` block
  is wrong; do not apply through it, because recreating the provider invalidates
  the working stage role's trust.
- `promote-prod.yml`, the prod branch of `destroy.yml`, and HTTPS
  (ACM + Route53 + 443 listener) are the rest of 9.1.
- Still true from 9.0: `infra/shared-ecr` has never been applied.
