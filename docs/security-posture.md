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
is the reviewer-gated GitHub Environment (ADR-0021).

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
