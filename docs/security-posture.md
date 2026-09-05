# Security posture of a public repository with a live AWS account behind it

Written 2026-07-26, Phase 11.1a, in answer to a direct question: **can a stranger
trigger a billable workflow, or reach a credential, now that the repository is
public (ADR-0022)?**

Short answer: no. Four independent locks, any one of which is sufficient. Each
claim below is followed by the command that re-checks it, because a claim about
state is not state.

## 1. Nothing billable is triggered by anything but a human with write access

```bash
grep -A6 '^on:' .github/workflows/*.yml
```

`deploy-stage`, `promote-prod` and `destroy` are `workflow_dispatch` only. No
`push`, no `pull_request`, no `schedule`. Dispatch — from the UI or the API —
requires **write** permission on the repository. Public is not writable: a
visitor has no Run workflow button and the API answers 403.

This was not always true. `deploy-stage.yml` used to trigger on push to `main`,
so every push raised billable infrastructure as a side effect. Removed in
6944229, before the repository was published.

`publish-site` is the one exception: it also triggers on `push` to `main` limited
to `site/**` and its own workflow file. That is deliberate — it creates no
billable infrastructure (S3 puts and one CloudFront invalidation), and pushing to
`main` requires the same **write** permission that dispatch does. There is no
`pull_request` trigger, so a fork cannot reach it.

## 2. `pull_request_target` does not appear anywhere

```bash
grep -rn 'pull_request_target' .github/
```

That trigger runs a fork's pull request in the **base** repository's context,
with access to its secrets, and is the standard escalation path out of a public
repository. There is not one instance of it here.

## 3. The one workflow a stranger can start has no route to AWS

`ci.yml` runs on `pull_request`, so a fork PR starts it. It declares
`permissions: contents: read`, does not request `id-token: write`, references no
secret, and never calls `configure-aws-credentials`:

```bash
grep -n 'id-token\|secrets\.\|configure-aws-credentials' .github/workflows/ci.yml
```

It builds a container and runs the Compose stack on GitHub-hosted runners, which
are free for public repositories. The compute it can waste is GitHub's, not this
account's. GitHub additionally requires maintainer approval for a first-time
contributor's fork PR.

## 4. Even a workflow that ran could not authenticate

The deploy roles trust the OIDC provider under three simultaneous conditions —
the federated principal, `aud = sts.amazonaws.com`, and a `sub` matching:

```text
repo:UVE-QA/aws-devops-sdet-demo:ref:refs/heads/main      stage only
repo:UVE-QA/aws-devops-sdet-demo:environment:<env>
```

A token minted for a fork carries that fork's `repo:` prefix and matches
nothing. See `infra/modules/iam_github_deploy_role/main.tf`. prod goes further:
`trust_branch_ref = false`, so it trusts **no branch at all** and its only path
is the GitHub Environment named `prod` (ADR-0021).

**That environment is no longer reviewer-gated (ADR-0068, 2026-09-05.)** The IAM
half is unchanged and still the stronger half: prod trusts no branch, and only a
job declaring `environment: prod` can assume the role. What is gone is the human
in front of it. Any run reaching that job proceeds, including one an anonymous
visitor started from the dashboard button — which is the point of the change and
also the whole of its cost. The public path is bounded by three launches a day,
one environment at a time, a promotion conditioned on a green stage, and a
teardown five minutes later; it is not bounded by a person any more.

Environment protection rules are UI state and git cannot assert them, so this
paragraph is the record and there is nothing in the repository that enforces it
— the same category as the fork-PR approval setting below and the NS delegation
in the parent zone.

## Backstops

- AWS Budgets, with both ACTUAL and FORECASTED notifications, is applied with
  every environment.
- The Terraform state bucket has all four public-access-block flags set
  (`infra/bootstrap/main.tf`), so the bucket name being public is inert without
  credentials.
- No static AWS key exists anywhere. The `vars.*` values are region, account id,
  owner and role ARNs — identifiers, not credentials. Publishing the account
  id was a decision, not an accident (ADR-0023).
- gitleaks over the full history, all refs: 81 commits, no findings
  (2026-07-26). The scan was verified capable of failing by running it against a
  throwaway repository containing a fake key.
- **Since Phase 15 (2026-07-28) that scan is a gate, not a memory.** `ci.yml`
  runs `make secret-scan` on every push and pull request, over the full history
  and every ref, with a pinned and checksum-verified gitleaks. The target refuses
  to run at all if the scanner is missing or the clone is shallow, because both
  produce the clean-looking empty result this project has been caught by before:

```bash
  make secret-scan     # needs gitleaks on PATH and a full clone
```

- **What that scan does and does not catch, measured rather than assumed
  (2026-07-28).** In gitleaks 8.30 an AWS access key ID on its own — `AKIA…` —
  is NOT a finding. A planted one scanned green through a real commit. The
  identifier together with a secret access key IS caught, by `generic-api-key`
  on entropy, not by `aws-access-token`. So the half that can spend money is
  caught and the half that cannot is not, which is defensible; what is not
  defensible is assuming the opposite, which is what everyone does.
- Dependabot watches all five dependency manifests (`.github/dependabot.yml`).
  It configures VERSION updates only; Dependabot **alerts** are a repository UI
  setting, in the same category as prod's protection rules — real, and invisible
  to every check in this repository.

## The infrastructure is scanned, and the exceptions are decisions

**Since Phase 15b (2026-07-28), `ci.yml` runs Checkov over `infra/` on every
push and pull request** — `make iac-scan`, the same target the devbox runs.

The first run reported **62 failures across 50 distinct checks**. Four were
cheap and real, and were fixed rather than skipped:

```text
CKV_AWS_131   the ALB now drops invalid header fields
CKV2_AWS_12   the VPC default security group is declared with no rules, which
              revokes the allow-all pair every VPC ships with
CKV2_AWS_32   the CloudFront distribution carries the managed security-headers
              policy (HSTS, nosniff, frame options, referrer policy, a CSP)
CKV_AWS_21    versioning on the dashboard bucket - status/, reports/ and
              timeline/ are written by the workflows and exist nowhere else,
              not in git
```

The remaining 46 are listed in `.checkov.yaml` with the reason beside each
group. They fall into three kinds, and the distinction is the point:

```text
forbidden by a decision   deletion protection on the ALB and the database
                          would break the teardown that is this project's
                          headline claim; the public subnet and the open egress
                          are the no-NAT design of ADR-0006
money the demo refuses    WAF, NAT, Multi-AZ, five CMKs, Container Insights,
                          Performance Insights, flow logs and three kinds of
                          access log are all metered
the scanner cannot see    infra/modules/alb terminates TLS only when a
                          certificate is passed. Checkov scans the module
                          standalone, cannot evaluate the `dynamic` block, and
                          reports the HTTP->HTTPS redirect as missing and the
                          TLS floor as absent on a listener that has no TLS
```

One skip is neither: RDS IAM authentication is free to enable and nothing here
would use it. Turning it on so a scanner stops asking would add something that
*reads* as a security control and is not one.

**The blind spot is stated in the file itself.** These skips are
repository-wide, so a new resource that violates one of them passes silently.
That is the price of a reviewable list over 46 inline annotations, and it is
why each group names the decision it rests on rather than just the check id.

**The gate was made to fail before it was trusted.** A security group opening
port 22 to the internet was committed into `infra/envs/stage`: three checks
fired (`CKV_AWS_23`, `CKV_AWS_24`, `CKV2_AWS_5`) and the target exited non-zero.
All three of its refusals were exercised too — scanner missing, config file
missing, and zero checks evaluated. The last one is not theoretical: **Checkov
on a directory containing no Terraform exits 0**, which is exactly the shape of
the empty-result trap this repository already carries a gitleaks refusal for.

## The image is scanned, and the actions are pinned

**Trivy runs over the image this commit builds** — not over a base image named
in a Dockerfile — in its own `ci.yml` job, with the scanner pinned by version
and verified by checksum. The gate is deliberately narrower than the report
(**ADR-0030** covers the pinning; this part is Phase 15b):

```text
a fix exists     stops the build. Actionable today.
no fix exists    printed on every run, not gated. A gate nobody can act on is
                 a gate people learn to ignore - but "not gated" must not
                 become "not known".
allowlisted      .trivyignore, reason on the line above the id, echoed back
                 next to the finding in the output.
```

**Both directions were observed in CI, on a real vulnerability rather than a
planted one.** The first run on `main` was RED: three HIGH findings in
`starlette`, a transitive dependency of FastAPI, fixed in 0.49.1, 1.1.0 and
1.3.1. Dependabot's PR #5 had independently proposed `fastapi 0.115.6 ->
0.140.13`, which resolves `starlette 1.3.1` — the version that clears all
three. Merging it turned the same gate green: `0 fixable, 23 with no fix
available`. The scanner and the bot arrived at the same fix from opposite
directions.

Those 23 are the Debian 13.6 base image — perl-base, util-linux, ncurses,
gzip, libacl1 — and they ship. They are visible in every run and in the
uploaded report.

**Every third-party action is pinned to a commit SHA** (ADR-0030), because
`aws-actions/configure-aws-credentials` is the step that turns an OIDC token
into AWS credentials in every AWS workflow, and it was floating on a mutable
`@v4` tag. 32 references, each carrying the version as a comment, and
`make action-pins` fails on any reference that is not a SHA, on any pin
without a version comment, and on finding no `uses:` lines at all.

## What is genuinely left, stated rather than hidden

**Actions logs on a public repository are world-readable.** Anything that
reaches the output of `terraform plan` or `apply` is public. No credential does.

`TF_VAR_budget_email` used to be the exception, and it was not hypothetical: a
GitHub *variable* is not masked, so the address appeared in the step environment
dump of every stage and prod run. **Fixed in Phase 15 (2026-07-28)**: it is an
environment *secret* in both `stage` and `prod`, referenced as
`${{ secrets.TF_VAR_BUDGET_EMAIL }}` by `deploy-stage`, `promote-prod` and
`destroy`, and Actions masks it. The remaining exposure is the shape of the
value, not the value: a masked field still tells a reader that a budget email
exists.

**The fork-PR approval setting is UI state, and git cannot assert it.** Same
category as prod's environment protection rules and the NS record in the parent
zone: real, load-bearing, and invisible to every check in this repository. The
GitHub default — approval required for first-time contributors — is adequate;
`Require approval for all external contributors` is the stricter setting.

**The actual threat model is the GitHub account, not the repository.** Every
lock above reduces to "you need write access". What protects write access is 2FA
on the account, and nothing in this repository can enforce that.
