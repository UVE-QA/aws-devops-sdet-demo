# Demo Script — ten minutes, live

For showing this project in an interview. It assumes nothing has been prepared
except what is in the "Before you start" section, and it is written so that the
ten minutes contain no waiting.

**The whole trick is that the cycle starts before the call, not during it.**
A cycle takes about fifteen minutes to a live prod, most of it RDS creating.
Measured on 2026-07-26: `deploy-stage` 16m05s, `promote-prod` 14m17s,
`destroy prod` 8m39s, `destroy stage` 8m31s. Repeated 2026-07-28:
`promote-prod` 14m08s, `destroy prod` 10m06s, `destroy stage` 8m34s. Nobody
will watch that, and it proves nothing that the run log does not prove
afterwards.

## Before you start — T minus 40 minutes

```text
1. Dispatch deploy-stage from the Actions tab.        ~16 min
2. When it is green, dispatch promote-prod with that
   run's commit SHA as image_tag, and approve it.     ~14 min
3. Confirm prod is really answering, from a host that
   has NOT been asking for the name (see the traps).
4. On the Mac, flush the resolver cache:
     sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder
5. Open the tabs, in this order:
     https://demo.uveapp.net
     https://app.demo.uveapp.net
     the repository
     the Actions tab
     the published Playwright report, from the dashboard
```

If you will show anything from the CLI, log in first — the token expires and an
expired token prints empty lists that look exactly like a clean account:

```bash
aws sso login --profile demo-admin --use-device-code
aws sts get-caller-identity --profile demo-admin
```

On the devbox, `--use-device-code` is not optional: the default flow opens a
callback on `127.0.0.1` that nothing there can reach.

## The ten minutes

### 0:00 — the dashboard (1.5 min)

Open https://demo.uveapp.net first, before any code.

> This page is itself a Terraform state level, and no destroy workflow can touch
> it. That is deliberate: the artifact that proves the teardown worked cannot be
> something the teardown deletes.

Point at the environment panels. They report what was **observed in AWS**, not
what a green pipeline implies. Say what each source can and cannot know: the
Actions API cannot know whether an environment exists, and a file written at the
end of a run cannot know a run is in progress — so the page holds two sources
and shows `unknown` when they disagree, naming the run it is waiting for.

### 1:30 — the shape of it (1.5 min)

Repository, `infra/`. Seven root levels: five permanent, two per cycle.

> Three of the five are permanent for the same reason, and each was found the
> hard way. The registry holds the image prod is running, so a stage teardown
> would have deleted it. The hosted zone outlives the load balancer. And the
> dashboard cannot live inside the thing it reports on.

`docs/decisions/` — twenty-seven ADRs. Mention that this is the one artifact
that cannot be reconstructed from the code afterwards.

### 3:00 — a cycle, per step (1.5 min)

The dashboard's current-cycle panel, then the same run in the Actions tab.

> Build once, tagged with the commit SHA. Apply. Migrate and seed run as ECS
> tasks against the real database, using the same task definition with an
> override — not a second image, not a shell on a box.

Say plainly that no human runs an AWS command during a cycle, and that all three
AWS workflows are dispatch-only: a push to `main` used to deploy billable
infrastructure as a side effect, and that is why it no longer triggers on push.

### 4:30 — what "tests green" means (1.5 min)

```text
tests/api/                          contract, destructive   stage + local
tests/playwright/tests/smoke/       read-only    the ONLY suite prod runs
tests/playwright/tests/regression/  destructive             stage + local
```

> Suites are bound to directories, so where a spec lives decides where it runs.
> That is not style: `promote-prod` used to run the whole test directory under a
> step named "read-only smoke against prod". It was true only while no
> destructive spec existed, and the first one would have made prod destructive
> silently.

Then open the published Playwright report from the dashboard.

> An Actions artifact needs a GitHub login to download. Publishing the report is
> what turns a test result into evidence someone outside can read.

If there is one thing to name here, name the database assertion: the regression
creates a row **through the browser**, and a separate process then looks that
exact row up in PostgreSQL.

### 6:00 — the approval gate (1.5 min)

Show the promote run pausing, or its log if it has already been approved.

> The gate has two halves and needs both. GitHub holds required reviewers on the
> `prod` environment. AWS holds the other half: prod's deploy role trusts only
> `environment:prod` and has no branch subject at all, so a workflow that skipped
> the environment could not authenticate. One boolean in IAM is the whole
> AWS-side enforcement.

Worth saying out loud: the GitHub half is UI state that git cannot assert, and
the project treats it as such — it is written down as a thing to re-check, next
to the manual NS record.

### 7:30 — promotion by digest (1 min)

Both environment panels on the dashboard at once.

> Stage shows a tag. Prod shows `@sha256:...`. Prod runs the exact bytes stage
> tested. Rebuilding the same commit would produce a different artifact and turn
> "tested in stage" from a fact into an assumption.

> A release is not the promotion. It is the moment the prod smoke goes green,
> and that moment writes three records or none of them: an immutable tag on the
> digest in the registry, an annotated tag on the commit in git, and a pointer
> in Parameter Store naming the last image that passed prod.

> When a release fails after prod has already been changed, the workflow
> re-applies that pointer's digest, waits for the service, and runs the smoke
> AGAIN before reporting anything — otherwise "rolled back" is a claim nobody
> checked. The run still fails: rollback is damage control, not a pass. And
> when there is nothing to roll back to, it refuses out loud and leaves prod
> standing for inspection rather than pretending it recovered.

If asked whether that has ever fired: yes, on purpose. A knowingly broken image
was promoted on 2026-07-28, the service never stabilised, prod was rolled back
and the re-run smoke proved it healthy — while the run stayed red.

### 8:30 — destroy (1 min)

Dispatch `destroy`, environment `prod`, confirm `DESTROY`. It stops at
`waiting` and asks for the same approval the deploy did — expect that, or it
reads live as a hung workflow. Approve it, then do not wait for it.

> The protection rule sits on the `prod` environment, not on the workflow, so
> tearing prod down is exactly as gated as deploying to it. Destroying `stage`
> does not pause at all. That asymmetry is the point: stage is for iteration,
> prod is guarded in both directions.

> The ALB is destroyed first, on purpose. Nothing in the configuration links it
> to the internet gateway, so Terraform destroys them concurrently and AWS
> answers DependencyViolation on the detach — the network interfaces are still
> attached. The fix is ordering in the workflow, because the two resources have
> no reference to each other.

The last step of the workflow asserts that nothing billable is left, scoped to
that environment, so destroying prod while stage is up does not fail a correct
teardown.

### 9:30 — what it costs (30 s)

> Between cycles: a state bucket, a small registry, one hosted zone and a
> CloudFront distribution serving one page. Cents. No NAT Gateway — that alone
> would be about $32 a month, more than everything else combined — and no EKS.
> Everything expensive exists only while a cycle is running.

Close on the dashboard, which is still up with both environments reported as
destroyed.

## Questions that get asked

```text
Why no NAT?             ~$32/month standing, versus a task in a public subnet
                        whose security group admits only the ALB. It is a real
                        trade-off and it is paid for in teardown ordering
                        (ADR-0016). VPC endpoints if it were ever revisited.
Why not EKS?            ECS Fargate already demonstrates container delivery.
                        EKS adds a control-plane cost and a large surface for
                        no additional story here.
Why one account?        Rejected a second workload account on schedule cost
                        (ADR-0017 D1); it is the one exclusion genuinely worth
                        revisiting later.
What is not tested?     The UI write path against PROD is covered by nothing
                        automated, by design, because prod runs read-only
                        suites. Say it before being asked.
Where is the state?     S3 with the native lockfile, one key per level, no
                        DynamoDB.
```

## Traps — each one has already cost time

```text
negative DNS cache   app.demo.uveapp.net is a dead name most of the time, so
                     resolvers cache the NXDOMAIN. On 2026-07-26 prod looked
                     dead in a browser for half an hour while serving 200s the
                     whole time: `dig` resolved and `curl` did not, because only
                     `curl` goes through the system resolver. Flush before the
                     demo, and verify prod from a host that has not been asking
                     for the name.
the RDS wait         5-10 minutes, every cycle. Never demo it live.
prod has no data     it is created and destroyed every cycle (ADR-0017 D2a).
                     Say so rather than being caught by an empty list.
expired SSO token    a teardown check with no credentials prints empty lists,
                     which is exactly what a clean account looks like. Run
                     `aws sts get-caller-identity` first, every time.
the approve button   the dashboard links to GitHub's approval page; it does not
                     approve. A page in a public bucket cannot hold a token that
                     writes to the repository. The price of the real version is
                     written down in docs/next-phases.md.
```

## If something breaks live

Nothing in the story depends on infrastructure being up at that moment. The run
history, the per-step panel and the published test report are all readable with
every environment destroyed — that is the property the dashboard was built for.
Say what you were about to show, show the run that already did it, and move on.

## After the demo

```text
1. destroy prod, then destroy stage, both from the Actions tab
2. confirm the verification step passed in each run
3. leave the dashboard up - it should now read "destroyed" for both
```

Anything left running bills by the hour. The teardown is part of the demo, not
housekeeping after it.
