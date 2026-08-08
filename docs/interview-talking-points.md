# Interview talking points

Per role, grounded in what is actually built and measured — not the plan. Every
claim here traces to an ADR, a session summary, or `docs/security-posture.md`.
If a phase in `docs/next-phases.md` is still open, it is named as open, not as
done. The project's own habit — "a claim about state is not state" — applies to
what gets said out loud about it, too.

The one-line framing, for whoever asks "what is this":

> A production-like AWS delivery platform for a minimal FastAPI app —
> Organizations-aware account isolation, Terraform across six state levels,
> GitHub Actions with OIDC and no static AWS keys, ECS Fargate behind an ALB,
> RDS Postgres, structured logging with a real CloudWatch alarm, Playwright test
> depth split by blast radius, and a teardown that is verified, not assumed.

## DevOps

```text
- Terraform split into SIX permanent state levels plus two that are
  destroyed every cycle (docs/architecture.md). All six are applied; the
  sixth went live in Phase 19b. The split exists because the container
  registry almost went the other way (ADR-0018): if it lived at the
  per-cycle level, a teardown would delete the image that PROVES the
  teardown works.
- GitHub Actions OIDC end to end, no static AWS keys anywhere - not
  "rotated regularly," not present at all. Verifiable in one grep
  (docs/security-posture.md §1-4).
- The qualifier, and it is a BETTER answer than the unqualified one
  (ADR-0034, live since Phase 19b). A public button on a static
  page reverses the one direction of trust: everywhere else GitHub
  authenticates to AWS over OIDC, and there AWS has to authenticate to
  GitHub, where no OIDC exists. So a long-lived GitHub credential enters
  the project, and the honest sentence becomes "no static AWS keys
  anywhere, and exactly one static GitHub credential, in Secrets Manager,
  readable by one Lambda role". The interesting part is not that none
  exists - it is that the one that does is scoped to a single permission
  on a single installation, rotated by a paste, and named in the design
  rather than found at interview.
- ECS Fargate, digest-based releases with automatic rollback (Phase 14,
  ADR-0029). The interesting correction: "roll back to the previous task
  definition" is meaningless in an environment destroyed every cycle - the
  previous revision is deregistered - so the rollback target had to become
  a digest pointer at a PERMANENT state level instead. Observed firing for
  real: a knowingly broken image was promoted, the service never
  stabilised, and the re-run smoke was green while the deploy run itself
  stayed red.
- destroy.yml runs a TARGETED destroy of the ALB before the rest of the
  network (ADR-0016), because Terraform has no dependency edge between the
  ALB and the Internet Gateway and destroys them concurrently otherwise -
  a DependencyViolation that took ~20 minutes to surface and was
  nondeterministic (a local destroy of the identical graph once succeeded).
- Full lifecycle - deploy, promote behind a required reviewer, smoke,
  destroy - runs through Actions with zero manual AWS operations, verified
  in a complete empty-to-empty run (Phase 13).
```

## Cloud Engineer

```text
- Dedicated AWS Organizations member account for the workload, separate
  from the management account by design (ADR-0001) - nothing is ever
  deployed into org-management.
- IAM Identity Center / SSO for human access; the deploy path is OIDC-only
  and trusts three simultaneous conditions per role (federated principal,
  aud, and a sub matching the exact repo+branch or repo+environment) -
  prod additionally sets trust_branch_ref = false, so it trusts NO branch
  at all, only the reviewer-gated GitHub Environment.
- No NAT Gateway, no EKS in v0 (ADR-0006) - the single largest cost lever
  in the design, and a defensible trade-off rather than an oversight: the
  app task gets a public IP but ingress is locked to the ALB security
  group, RDS stays publicly_accessible = false, reachable only from the
  ECS security group.
- A public repository with a live AWS account behind it, and the actual
  answer to "can a stranger reach it" is documented as four INDEPENDENT
  locks, any one sufficient (docs/security-posture.md) - dispatch-only
  workflows requiring write access, no pull_request_target anywhere, the
  one stranger-triggerable workflow (ci.yml) never touching AWS at all,
  and the OIDC trust conditions rejecting a fork's token regardless.
- DNS delegated into the demo account (ADR-0024) with the delegation
  itself documented as the one thing git cannot see - a manual NS record
  in the parent zone, plus a second, unrelated hosted zone for the same
  apex domain in a different account that looks complete and isn't
  authoritative. Ground truth is `dig ... @a.gtld-servers.net`, not the
  console.
```

## QA Automation / SDET

```text
- Four test suites, separated by DIRECTORY and bound to distinct Playwright
  projects specifically because they differ in blast radius (ADR-0025):
  tests/unit (in-process, no network), tests/api (destructive HTTP
  contract), tests/playwright/smoke (read-only - the only suite prod ever
  runs), tests/playwright/regression (destructive, stage-only), tests/db
  (seed assertion as an ECS task).
- tests/unit exists for a reason invisible to any HTTP client: the 5xx
  CloudWatch alarm reads the application's OWN log, so whether `status` is
  serialised as a JSON number or a string, and whether an unhandled
  exception is logged at all, is a contract that no black-box test can see
  (ADR-0032).
- A concrete example of test depth catching something review missed: a
  deliberate off-by-one in pagination (.offset(offset + 1)) passed all 50
  contract tests, because every existing assertion checked the newest rows
  and an off-by-one drops the oldest ones instead - only a break test
  written for that specific failure mode caught it.
- Another: a Playwright spec that skipped itself on its FIRST run reported
  the same green colour as a pass, because its fixture didn't exist yet -
  found by building the fixture and watching the skip become a real
  result, not by reading the spec.
- Database assertions after a UI action distinguish an UPDATE from an
  INSERT with the same name, by renaming a row through the browser and
  reading updated_at back from Postgres (Phase 16a) - the test proves the
  right SQL operation happened, not just the right final state.
- The house rule that produced all of the above: "a gate that has only
  ever been seen GREEN is indistinguishable from a gate that cannot fail."
  Fifteen gates in this project have been deliberately broken once, on
  purpose, with the RED output kept as evidence (docs/session-primer.md).
```

## Security

```text
- No static AWS keys anywhere, ever - OIDC-issued temporary credentials
  only, scoped per environment (docs/security-posture.md).
- Secret scanning (gitleaks) over the FULL git history and every ref, as a
  CI gate, not a one-time check - and the project can state its own blind
  spot precisely: gitleaks 8.30 does not treat a bare AWS access key ID
  (AKIA...) as a finding on its own; only the id+secret PAIR is caught, by
  an entropy rule rather than the AWS-specific one. This was discovered by
  a break test that FAILED TO BREAK - a planted key scanned green - which
  is a more honest finding than a break test that behaves as expected.
- IaC scanning (Checkov) over infra/ on every push: 62 findings on the
  first run, 4 fixed as real gaps (invalid ALB headers, an unrestricted
  default security group, missing CloudFront security headers, missing
  bucket versioning on a bucket the workflows write to directly), and 46
  documented SKIPS grouped by the decision each rests on - not silenced,
  reasoned about in one reviewable file (.checkov.yaml).
- Image scanning (Trivy) gated on findings that HAVE a fix, reporting
  (not blocking on) the ones that don't - observed going red-then-green in
  CI on a REAL starlette CVE, not a planted one, with Dependabot's PR
  independently proposing the exact upgrade that resolved it.
- Every third-party GitHub Action pinned to a commit SHA (ADR-0030, 32
  references) rather than a mutable tag - the credential-minting step
  (configure-aws-credentials) was floating on @v4 before this.
- The one exposure the project states rather than hides: budget email used
  to leak into public Actions logs because a GitHub *variable* is not
  masked; fixed by moving it to an environment *secret* in Phase 15. And
  the honestly-stated remaining gap: the real perimeter is the GitHub
  account's own 2FA, and nothing in the repository can enforce that.
```

## FinOps

```text
- Per-cycle infrastructure (ALB + Fargate + RDS) is destroyed after every
  demo, not left running - two measured full stage+prod cycles cost
  roughly $0.09 and $0.17 at list prices (docs/cost-control.md). An
  always-on prod at the same shapes would run $40-60/month (ADR-0017),
  which is the number that forced prod to be on-demand rather than
  always-up in the first place.
- A hard architectural choice made for cost, stated as a trade-off rather
  than hidden: no NAT Gateway (ADR-0006), which is billed hourly plus
  per-GB the entire time an environment is up, whether used or not - the
  single largest lever in the whole design.
- AWS Budgets applied to every environment: ACTUAL spend alerts at 50% of a
  $20/month limit, FORECASTED at 100%, notification to an environment
  secret (not a variable, so it can't leak in logs). Free to run; the
  failure mode it exists for - an environment forgotten and left up - is
  the project's single most expensive plausible mistake.
- Only 5 of the 46 Checkov skip decisions are safety-relevant at all; the
  rest are explicitly "money the demo refuses" - WAF, NAT, Multi-AZ RDS,
  five customer-managed KMS keys, Container/Performance Insights, flow
  logs, and access logging on multiple resources - each named as a
  decision rather than an unexamined gap.
```

## Questions this document does not answer on purpose

Phase 17 (persistent prod data) is planned and optional, and Phase 20 (the cycle
made visible on the dashboard without opening a log) is planned, not built. If
asked "does it do X" for either, the honest answer is "designed, not shipped -
here's why it's next" rather than describing it as done.

Phases 18 and 19 ARE built, and this paragraph said otherwise for six days after
19 shipped. That is worth telling on purpose rather than hiding: five documents
here described the self-service launch as unapplied while a public button had
been live for a week, and none of the project's gates could see it, because
`make docs-check` verifies that every path and target a document NAMES exists -
not that what a document CLAIMS is true. Phase 20's first sub-phase generates the
architecture section from the repository for exactly that reason.
