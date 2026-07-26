# 2026-07-26 — Phase 11.1a: decisions, scaffold, and the public-repo question

Chat-driven session. Nothing was applied to AWS; nothing in it is billable.
State was loaded by cloning `origin/main` fresh — the sandbox already held a
clone from an earlier chat, which is exactly the copy ADR-0019 says not to
trust, so it was discarded rather than read.

## What was done

### The Phase 11.0 debt, paid first

`gitleaks` over the **full history, every ref**, on the devbox:

```text
81 commits scanned, ~572 KB, no leaks found, exit 0
```

Then the same invocation against a throwaway repository in `/tmp` containing one
fabricated key:

```text
Finding: REDACTED, RuleID generic-api-key, exit 1
```

and `git rev-list --all --count` returned **81**, matching what gitleaks said it
had scanned. Three separate things, none of which the others imply: that the
scan found nothing, that the scan covers every ref rather than HEAD, and that the
scan is capable of reporting a finding at all.

A small observation worth carrying into Phase 15, where gitleaks goes into CI:
the fake `AKIA…` key was caught by the entropy-based `generic-api-key` rule, not
by the AWS-specific one. When the CI gate is wired, assert on the AWS rule
specifically rather than on "something was found".

### ADR-0026 — dashboard status comes from two sources

The plan left the question open: GitHub Actions API, or a status file written by
the workflows. The framing dissolved it. They answer different questions and
neither can answer the other's:

```text
Actions   knows where a run is; knows nothing about what exists in AWS.
          "The last destroy was green" is a statement about a workflow.
status.json  knows what was in AWS when it was written; cannot know a run
          is in progress, because it is written after that point.
```

So: both, and a rule that decides every future addition — **a source may only
assert what it observes.** Each carries a run id, so each detects the other going
stale, and the page renders "unknown" rather than a stale value when the newest
run is younger than the file. The unauthenticated GitHub rate limit (60/hour/IP)
is accepted and degrades visibly, because an empty result is not a clean result.

### ADR-0027 — the dashboard is a permanent state level

`infra/public-site`, key `public-site/terraform.tfstate`, applied locally, never
referenced by `destroy.yml`. Third instance of one rule, and the sharpest:

```text
ADR-0018  the registry     stage's teardown would delete prod's image
ADR-0024  the hosted zone  recreating it breaks a delegation in another account
ADR-0027  the dashboard    the exhibit cannot be destroyed by what it exhibits
```

Private bucket behind CloudFront OAC rather than a public bucket or GitHub
Pages — hosting the showcase of an AWS project outside AWS would demonstrate
none of the skills the project is about, and a public bucket is the easy wrong
answer every review flags. The certificate must be issued in **us-east-1**,
while the prod ALB's stays regional: two certificates, two regions, one domain,
which is why the level declares a second provider with `alias = us_east_1`.
`infra/dns` had already left the apex out of its wildcard SANs for exactly this
reason — a comment written in a previous phase that turned out to be a plan.

### The scaffold

`infra/public-site/{backend,main,variables,outputs}.tf` and
`terraform.tfvars.example`. Bucket blocked to the public on all four flags,
bucket policy naming the distribution ARN as `AWS:SourceArn` so it grants
CloudFront-in-general nothing, apex and `www` alias records, and a publish role
that trusts `environment:stage` and `environment:prod` and **no branch**, scoped
to this bucket and this distribution. Nothing applied.

### docs/security-posture.md

Written in answer to a question asked directly during the session: with the
repository public, can a stranger start a billable workflow or reach a
credential. Four independent locks, each with the command that re-checks it —
dispatch-only triggers on all three AWS workflows and dispatch requires write
access; no `pull_request_target` anywhere; `ci.yml` is the only workflow a
stranger can start and it requests no `id-token`, uses no secret and never
configures AWS credentials; and the OIDC `sub` is scoped to this repository plus
a branch or environment, which a fork's token cannot match.

The valuable half is the residue, named rather than buried:

```text
Actions logs are world-readable on a public repo, and TF_VAR_budget_email
  travels in the job environment. An address, not a key — but a choice.
The fork-PR approval setting is UI state git cannot assert. Same category as
  prod's protection rules and the NS record in the parent zone.
The real threat model is the GitHub account, not the repository. Every lock
  above reduces to "you need write access", which 2FA protects and this
  repository cannot.
```

## Validation

Run on the devbox after the patch landed, both green on the first attempt:

```text
terraform fmt -recursive -check infra     exit 0, no output
make tf-validate                          OK x7, including infra/public-site
```

The seven include the new level because `tf-validate` DISCOVERS root levels with
a `find` expression rather than reading a list, so a level cannot be added
without being validated. The discovery itself was printed and counted rather than
assumed — an empty discovery that exits 0 is a failure this project has already
had once (e1e577a).

The documents above were written before this ran, which is the normal shape here
and not an oversight: the patch has to reach the devbox before anything can be
run there, so a session produces one patch with the work and a second, small one
recording what the validation showed.

```bash
terraform fmt -recursive -check infra
make tf-validate      # root levels must go from 6 to 7
```

Terraform is not installed in the chat sandbox and could not be downloaded there,
so the HCL was written without a local `fmt` pass. Alignment was pre-checked with
a throwaway script that reproduces the `=` alignment rule; the script was itself
verified by breaking a line on purpose and confirming it went red, and by running
it clean over `infra/dns` and `infra/envs/prod`.

That script is a proxy for `terraform fmt`, not a substitute, and the session
said so and budgeted one correction round. **No correction was needed** — kept
here as a wrong prediction rather than edited away, because the reasoning behind
it stays the right default for the next person writing HCL blind.

## Follow-ups this session did not touch

- the `teardown` skill lists four permanent levels; it becomes five in 11.1b,
  with the apply, not before.
- `TF_VAR_budget_email` in public plan output: accept, or move to a Secret.
- fork-PR approval setting: consider `Require approval for all external
  contributors`.
- the stray `demo` NS record in the non-authoritative zone (account
  478937318617), and the unused `TF_STATE_BUCKET` variable on the stage
  environment, both still outstanding from Phase 9.
