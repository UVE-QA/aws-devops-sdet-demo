# Session 2026-07-26 (second) — Phase 9.1 closed: prod, promotion, HTTPS

- Phase: 9.1. **CLOSED.** The full cycle now runs for two environments.
- Request: finish 9.1 in order — apply the permanent levels, write the promotion
  path, then HTTPS on the existing domain.
- Tooling: Cowork chat driving, devbox executing, delivery as `git am` patches.
  `gh` was installed on the devbox during the session and carried the rest of it:
  workflow dispatch, run logs, environment variables, and the reviewer approval.
- Cost: one full cycle of stage + prod (roughly 45 minutes of ALB/RDS/Fargate),
  plus a permanent hosted zone at ~$0.50/month. Everything billable was destroyed
  before the session closed, verified against the AWS CLI.

## Result

The closing criterion of Phase 9.1 was met end to end, through Actions, with no
manual AWS operation:

```text
deploy-stage  #  green, 14m13s   image ec01570 built and pushed
promote-prod  #  PAUSED for required reviewers, approved, green 13m24s
              #  promoted BY DIGEST - no rebuild
https://app.demo.uveapp.net -> 200, certificate verified by curl
destroy prod  #  green 8m28s, verification passed WHILE STAGE WAS STILL UP
destroy stage #  green 8m24s
```

Independent verification after teardown, against the AWS CLI rather than
Terraform state: ECS, RDS, ALB, NAT, EKS, unattached EIPs, non-default VPCs and
Secrets Manager all empty; ECR, the hosted zone and the two deploy roles remain
by design; `app.demo.uveapp.net` no longer resolves, because the alias record is
per-cycle state and left with the environment.

```text
2df169a  fix(destroy): scope the leftover check per environment, and wire prod
f776458  ci: promote to prod by digest, behind the reviewer gate
e70c483  feat(dns): HTTPS for prod on a delegated subdomain (ADR-0024)
ca971ee  fix(dns): ACM rejects an asterisk in a tag value
25d4dab  fix(iam): two reads the Route53 and ACM data sources actually make
```

Applied locally under `demo-admin`: `infra/bootstrap-oidc` (prod deploy role,
then twice more for policy changes), `infra/shared-ecr` (first apply ever),
`infra/dns` (new permanent level).

## Finding 1 — the teardown verification would have failed a correct teardown

`destroy.yml` asserted that nothing matching `aws-devops-sdet-demo` remained
**anywhere in the account**. That is right only while exactly one environment can
exist. With prod alive, tearing down stage would have found prod's ECS cluster,
RDS instance and ALB and failed — reporting a teardown bug where there was a
check bug, at the end of a run, in the step whose whole job is to be trustworthy.

Found by reading the workflow before running it, fixed in the same session, and
then **proven by the cycle itself**: prod was destroyed while stage was still up
and the verification step passed. This is the first defect in this project caught
before its first run and confirmed by that run in the same sitting.

The account-wide assertions (NAT, EKS, unattached EIPs) deliberately stayed
account-wide. They are statements about the v0 architecture, not about one
environment, and narrowing them would have weakened the check while pretending to
fix it.

## Finding 2 — two IAM reads that no reading of the code would reveal

`promote-prod` #1 failed at `terraform plan` with two `AccessDenied` errors:

```text
route53:ListTagsForResource   issued by the aws_route53_zone DATA SOURCE
acm:GetCertificate            issued by the aws_acm_certificate DATA SOURCE
```

Neither call is implied by the configuration. Nothing in `infra/envs/prod` asks
for zone tags or a certificate body; the provider makes those calls anyway. The
action list had been derived from what the configuration appears to need, which
is exactly the mistake ADR-0016 already paid for with
`iam:ListInstanceProfilesForRole` and ADR-0018 flagged under **Watch**.

There is no way to catch this by inspection. The only detector is running the
path, and the cost of running it is one failed plan — cheap, as long as the phase
budgets for a first run that fails.

## Finding 3 — the hosted zone that looked authoritative was not

The delegation record for `demo.uveapp.net` was first created in a hosted zone
for `uveapp.net` that had everything a real zone has — MX for SES, DKIM CNAMEs,
`api`, `serverless`, sibling delegations — and served nobody. Its delegation set
did not match what the `.net` registry publishes. The live zone turned out to be
in `org-management`, holding four records.

Recorded in ADR-0024 along with the two diagnostic mistakes that stretched this
to nearly an hour:

- the ground truth for a delegation is the TLD, not the console:
  `dig +noall +authority NS <domain> @a.gtld-servers.net`;
- `dig +short` prints ANSWER only, so a referral (NS in AUTHORITY) and a
  wrong-type query (`NS` at a name holding `A`) both come back empty and both
  read as "the record is missing".

## Finding 4 — `make tf-validate` leaked 4.5GB per run

`TF_DATA_DIR=$(mktemp -d)` per root level, never removed. Every run left one full
provider download (~700MB) per level in `/tmp`. The disk was at 99% of 58GB and
an unrelated `terraform init` died with "no space left on device"; ~47GB was
reclaimed by deleting the leaked directories.

The isolation itself is correct and stays — it is what Phase 9.0 added to stop
`init -backend=false` silently reusing a cached S3 backend. Fixed with one
temporary root removed by a `trap`, plus a shared `TF_PLUGIN_CACHE_DIR` so the
provider is fetched once per machine rather than once per level per run.

## Smaller things

- **ACM rejects `*` in a tag VALUE.** `RequestCertificate` returns a 400 on
  `tags.4`. The wildcard is legal in `domain_name`, illegal in the `Name` tag.
- **A headless devbox needs `aws sso login --use-device-code`.** The default flow
  opens a `127.0.0.1` callback that resolves to the laptop's loopback, not the
  devbox's.
- **`TF_STATE_BUCKET` is referenced by nothing** — not a workflow, not a backend
  block (those hardcode the bucket). It survives as a GitHub Environment variable
  on `stage` and was deliberately NOT copied to `prod`. Deleting it is left as an
  explicit follow-up rather than a silent UI edit.
- **Node 20 deprecation** is annotated on every run: `actions/upload-artifact@v4`,
  `aws-actions/configure-aws-credentials@v4` and `hashicorp/setup-terraform@v3`
  are being forced onto Node 24. Harmless today, a red build eventually.
- **A stray `demo` NS record** remains in the non-authoritative copy of the zone
  in account 478937318617 and should be deleted.

## What Phase 9.1 leaves behind

The MVP finish line named in `docs/next-phases.md` is now missing only its
dashboard: one button deploys stage, tests gate it, a human approves, prod comes
up on its own HTTPS name, one button destroys everything. The remaining MVP work
is Phase 10 (a thin application slice, so "tests green" means something) and
Phase 11 (the public dashboard).

A requirement for that dashboard came out of this session: it should show the
**stages of a run with their status**, not just a final colour. Two candidate
data sources, to be settled by an ADR in Phase 11 — reading the GitHub Actions
API directly from the browser (the repository is public, so no backend and no
token), or having the workflows write a status document into the same bucket.
