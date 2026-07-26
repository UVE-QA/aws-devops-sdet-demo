# ADR-0027: The public dashboard is a permanent state level, served from S3 behind CloudFront

## Status
Accepted (Phase 11.1). Third application of the reasoning in ADR-0018 and
ADR-0024. Implements ADR-0017 D2 and D4 Wave A.

## Context

The dashboard's whole purpose is to be online when nothing else is — to show,
to someone with no GitHub account and no AWS access, that both environments are
destroyed and that this is the normal state of the project rather than an
outage. That is the phase's closing criterion, and it is also the constraint
that decides where the dashboard lives.

If it lived in `infra/envs/*`, the teardown would delete the artifact that
proves the teardown works. This project has now met that shape three times:

```text
ADR-0018  the container registry  — stage's teardown would delete the image
                                    prod had promoted
ADR-0024  the hosted zone         — recreating it reassigns name servers and
                                    breaks a delegation in another account
ADR-0027  the dashboard           — the exhibit cannot be destroyed by the
                                    thing it exhibits
```

The rule underneath all three, stated once so the fourth case is recognised
faster: **anything that must survive a teardown belongs above the environment
levels** — including, especially, the evidence that the teardown happened.

## Decision

A new permanent root level:

```text
infra/public-site/     key public-site/terraform.tfstate, same bucket
                       applied LOCALLY under demo-admin
                       never referenced by destroy.yml
```

It contains: a private S3 bucket, a CloudFront distribution with Origin Access
Control, an ACM certificate in **us-east-1**, Route53 records for the apex and
`www` of the delegated zone, and the narrow publish role of ADR-0026.

### Private bucket behind OAC, not a public bucket, not GitHub Pages

Pages is free and simpler, and hosting the showcase of an AWS project outside
AWS would demonstrate none of the skills the project exists to demonstrate. A
public bucket is the easy wrong answer: it works, and it is the pattern every
security review flags. S3 blocked to the public and reachable only through an
Origin Access Control identity, with the bucket policy naming the distribution,
costs the same cents per month and is itself an exhibit worth pointing at.

### Two certificates, two regions, one domain

CloudFront can only use a certificate issued in `us-east-1`. The prod ALB can
only use one issued in its own region. So:

```text
us-west-2   *.demo.uveapp.net   infra/dns, terminated by the prod ALB
us-east-1   demo.uveapp.net + *.demo.uveapp.net   infra/public-site, CloudFront
```

This is not duplication to be tidied away later. `infra/dns` already anticipated
it in a comment: the apex was deliberately left out of the wildcard's SANs
because the apex is served by CloudFront, which could not have used that
certificate anyway. The us-east-1 certificate needs the apex, because that is
where the dashboard lives.

Consequently `infra/public-site` declares a second `aws` provider with
`alias = us_east_1`, used only for the certificate and its validation.

### The zone is looked up, not read from another level's state

The DNS validation records and the alias records go into the zone owned by
`infra/dns`, but this level reads that zone with a `data` source by name rather
than through a remote state lookup — the same pattern prod already uses for the
ALB certificate. The levels stay coupled by a domain name, which is a fact about
the world, instead of by a state file layout, which is an implementation detail.

### DNS layout

```text
demo.uveapp.net        A/AAAA alias -> CloudFront   always up
www.demo.uveapp.net    A/AAAA alias -> CloudFront   always up
app.demo.uveapp.net    A alias -> prod ALB          on demand, dead most of the time
```

## Consequences

- One more permanent level to apply on a fresh account, after `infra/dns` and
  before anything needs to publish. `docs/preflight-inventory.md` ordering grows
  by one step.
- Cost: cents per month — S3 storage measured in megabytes, CloudFront at
  portfolio traffic, and a certificate, which is free. It is fixed and it is
  permanent, which is exactly the trade being made: the dashboard is worthless
  if it is only up when the demo is.
- Creating and propagating a CloudFront distribution takes roughly 10-15 minutes.
  That is a **one-time** cost at apply, not a per-cycle cost, and it is the
  reason this level must never sit inside a cycle.
- Deleting a distribution requires disabling it first and waiting. Anyone
  tearing this level down by hand should expect two passes; there is no destroy
  workflow for it by design.
- **The teardown skill lists the levels a destroy must not touch, and there are
  now five, not four.** That edit belongs in Phase 11.1b, with the apply — not
  here, because a document in this repository must not describe as existing in
  AWS something that has only been scaffolded in git. It is recorded as a
  closing criterion of 11.1b so it cannot be forgotten.
- `status.json` and the Playwright HTML report are published into this bucket by
  the workflows (ADR-0026), which is what turns test results from a
  login-gated GitHub artifact into public evidence.
