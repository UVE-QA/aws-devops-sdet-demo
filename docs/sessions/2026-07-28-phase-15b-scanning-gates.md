# 2026-07-28 — Phase 15b: Trivy, Checkov, and pinned actions

Second half of the supply-chain phase. 15a was wiring; this half was triage,
as predicted in `docs/next-phases.md`, and the prediction held: 62 Checkov
failures and 26 HIGH/CRITICAL container findings, of which the decisions took
the session and the wiring took about an hour.

$0. Nothing was applied to AWS and no environment existed at any point.

## Delivered

```text
patch A   the four Checkov findings worth fixing, then Checkov as a gate
patch B   Trivy over the built image, gated on what is fixable
patch C   32 actions pinned by commit SHA, ADR-0030, closing documents
```

Three patches, and the reason is the usual one: reality got a word in twice.
Patch B could not be written before the devbox produced a checksum for a
pinned Trivy, and patch C could not be written before the pinning question was
answered.

## Checkov

62 failures across 50 distinct checks on the first run.

**Four were fixed rather than skipped**, all free:

```text
CKV_AWS_131   the ALB drops invalid header fields
CKV2_AWS_12   the VPC default security group is declared with no rules, which
              revokes the allow-all pair every VPC ships with. It is ADOPTED,
              not created: destroy drops it from state and it goes with the VPC
CKV2_AWS_32   the managed security-headers policy on CloudFront, resolved BY
              NAME through a data source - a wrong name fails at plan time with
              something readable, a wrong GUID fails at apply with an id nobody
              can look up
CKV_AWS_21    versioning on the dashboard bucket. status/ and reports/ are
              written by the lifecycle workflows and exist nowhere else; 11.1b
              already added a guard against the sync deleting them, and this is
              the half that survives the guard being wrong
```

**46 are skip decisions**, grouped in `.checkov.yaml` with the reason beside
each group: forbidden by a recorded decision (deletion protection would break
the teardown that is the headline claim; the public subnet and open egress are
the no-NAT design of ADR-0006), money the demo refuses (WAF, Multi-AZ, five
CMKs, Container Insights, Performance Insights, flow logs, three kinds of
access log), or something the scanner cannot evaluate.

One skip is none of those and is called out separately: RDS IAM authentication
is free to enable and nothing here would use it. A feature switched on so a
scanner stops asking reads as a security control and is not one.

**Four of the 46 are the tool, not the posture.** `infra/modules/alb`
terminates TLS only when a certificate is passed. Checkov scans the module
standalone, cannot see through the `dynamic` default_action or the `count`-ed
HTTPS listener, and reports the redirect as missing and the TLS floor as absent
on a listener that has no TLS to configure. The half that is NOT a false
positive: stage really does serve plain HTTP, deliberately (ADR-0017 D3).

**The blind spot is written into the config.** These skips are
repository-wide, so a new resource violating one passes silently. That is the
price of a reviewable list over 46 inline annotations, and it is why each group
names the decision it rests on rather than only the check id.

## Trivy

The scan runs with `--exit-code 0` and **without** `--ignore-unfixed`, so the
uploaded report holds every HIGH and CRITICAL. The verdict is made in
`scripts/summarise-trivy.py`, where it can be read: findings with a fix stop
the build, findings without one are printed on every run and not gated, and
`.trivyignore` carries exceptions with the reason echoed back next to the id.

Gating on unfixable findings produces a build that stays red until a stranger
ships something, which teaches people to ignore the gate. Not gating on them
must not quietly become not knowing about them, which is why they print.

**Both directions were observed in CI, on a real vulnerability.**

```text
ci #89   RED    3 fixable, all starlette: CVE-2025-62727, CVE-2026-48818,
                CVE-2026-54283, fixed in 0.49.1, 1.1.0 and 1.3.1
merge #5        dependabot: fastapi 0.115.6 -> 0.140.13
ci #91   GREEN  0 fixable, 23 with no fix available
```

The convergence was checked, not assumed: `fastapi==0.140.13` was installed
into a clean virtualenv and resolved `starlette 1.3.1` — the exact version that
clears all three. The scanner and the bot reached the same fix independently.

The 23 remaining are the Debian 13.6 base: perl-base, util-linux, ncurses,
gzip, libacl1. They ship, visibly.

**The red was chosen.** Merging #5 first would have made the first-ever run of
the `image-scan` job green, and a job that has only ever been seen green is
indistinguishable from one that cannot fail. Five minutes of red `main` bought
a CI-level break test on a genuine CVE. Nothing deploys on push, so it cost
nothing else.

## Pinning — ADR-0030

Answered YES. 32 references across five workflows, pinned to commit SHAs with
the version as a required comment, and `make action-pins` in `ci.yml` to keep
it from decaying on the first step somebody adds.

The threat is specific rather than generic here: four workflows hold
`id-token: write` and assume an AWS role, and
`aws-actions/configure-aws-credentials` — the step that performs that exchange
in every one of them — was floating on a mutable `@v4` tag, two majors behind.

SHAs were resolved with `git ls-remote https://github.com/owner/repo
refs/tags/vX.Y.Z^{}`, a verifiable operation against the repository rather than
a value copied out of a rendered page. The checker prints that command when it
fails.

PR #3 was closed as superseded rather than merged: pinning straight to the SHAs
of the same versions is the identical upgrade in one commit.

## What running it showed that reading it would not

**A gate on a shared dependency reddens every open pull request.** The moment
`image-scan` reached `main`, PRs #1, #2, #3 and #4 all failed on the same three
`starlette` findings, none of which they introduced. Until #5 landed, none of
the four carried a signal about its own contents. Obvious afterwards; it was
not on the list beforehand.

**Checkov on a directory with no Terraform exits 0.** Verified rather than
assumed, and it is the same shape as the gitleaks trap this repository already
carries a refusal for. `summarise-checkov.py` refuses when nothing was
evaluated.

**The devbox did not have Checkov.** The refusal said so before anything could
pass — the same finding as gitleaks in 15a, two days later. The pattern is now
established enough to state: a scanner this project declares mandatory is not
on the machine this project develops on until a refusal says so.

**A break test measured with a pipe measures the pipe.** The first Checkov
break test printed three red checks and `make exit=0`, which read exactly like
15a's gate that would not break. The gate was fine; `$?` after `| grep` is
grep's status. One correct re-measurement separated the two in a few seconds —
but the first reading was indistinguishable from a real defect, and that is the
point: an instrument has to be trusted before its verdict means anything.

**Restoring a file with `git checkout` after a break test discards uncommitted
work.** A pinning edit to `ci.yml` was silently reverted mid-session, because
the file's pins were not committed yet. Commit before breaking things on
purpose.

## Validation

Identical numbers on both hosts, which is the property `make` targets are
supposed to buy:

```bash
make iac-scan       # checkov 3.3.8, 46 skipped by decision, 177 passed, 0 failed
make image-scan     # 0 fixable, 23 with no fix available, 0 allowlisted
make action-pins    # 32 action references, all pinned to a commit SHA
make docs-check     # 6 documents, 0 findings
terraform fmt -check -recursive infra
make tf-validate
```

## Follow-ups

```text
- deploy-stage, promote-prod, destroy and publish-site are dispatch-only, so
  setup-terraform v3->v4 and configure-aws-credentials v4->v6 are proven only
  by the next full cycle. If it breaks, the version bump is the suspect; the
  pin half is inert by construction.
- PRs #1, #2 and #4 are green and merge whenever convenient - they touch test
  manifests that ci exercises fully.
- the Node 20 deprecation annotations should be gone after patch C. Check.
- Checkov on the devbox lives in a venv symlinked into /usr/local/bin. That
  install is not recorded anywhere a rebuild would find it; it belongs in
  docs/lightsail-devbox.md when Phase 18 writes it.
```
