# ADR-0024: A delegated subdomain, and DNS as a permanent state level

## Status
Accepted (Phase 9.1). Implements ADR-0017 D3 ("public HTTPS on an existing
domain") and extends the state-level model of ADR-0018.

## Context

Phase 9.1 needs `https://app.<domain>` to serve prod with a valid certificate.
The domain that exists is `uveapp.net`. Its Route53 hosted zone lives in account
`478937318617` (`vlad.urban.qa`), which is **not a member of this Organization**
and is not reachable through this project's IAM Identity Center — that portal
lists exactly four accounts: `devops-sdet-demo` (993912191738),
`org-management`, `proj-eu-vpn`, `proj-sandbox`. There is no credential path
from this project into the domain's account, by construction rather than by
oversight.

That zone already delegates sibling subdomains — `files.uveapp.net` and
`who.uveapp.net` both carry `NS` records — so delegation is the established
pattern there, not a mechanism invented for this project.

The record that matters is not static. The ALB is created and destroyed with
every cycle (ADR-0017 D2a), so its DNS name is different on every deploy, and
the record pointing at it must be written by the same automation that creates
the ALB — that is, by Terraform running under the prod deploy role, inside the
demo account. Any design in which a human edits a record per cycle fails the
project's own standard: the cycle must run with no manual AWS operation.

So the question is narrow: how does automation running in the demo account get
authority over a name under `uveapp.net`, given the parent zone lives in another
account in another organization?

The certificate carries a second, quieter question. ACM validates by DNS and
takes minutes. If the certificate lives in the environment, it is re-issued and
re-validated on every cycle — minutes added to a path whose entire purpose is
being repeatable, and a new way for a deploy to fail that has nothing to do with
the software being deployed.

## Decision

1. **Delegate a subdomain, do not move the domain.** `demo.uveapp.net` is
   delegated to the demo account. The parent zone keeps a single `NS` record for
   that label, pointing at the four name servers of the delegated zone. Prod is
   published at `app.demo.uveapp.net`.

2. **A new permanent state level `infra/dns/`** holds the hosted zone for
   `demo.uveapp.net` and a wildcard ACM certificate for `*.demo.uveapp.net`,
   with its DNS validation records and an `aws_acm_certificate_validation` gate.
   Own state key `dns/terraform.tfstate`. Applied locally under
   `AWS_PROFILE=demo-admin`, once per account. No destroy in the normal
   lifecycle.

   It is permanent for two independent reasons, either sufficient. Recreating the
   zone assigns **new name servers** and silently breaks a delegation this
   project has no credentials to repair. And a certificate that is issued once
   removes both the wait and the failure mode from every subsequent cycle.

3. **The alias record stays in `infra/envs/prod`.** It is per-cycle state: it
   points at an ALB that will not exist next week. The zone survives the
   teardown; the record does not.

4. **The environment consumes the zone and the certificate BY NAME**, through
   `data "aws_route53_zone"` and `data "aws_acm_certificate"`, not by reading
   `infra/dns`'s state. The two levels share a domain name and nothing else, and
   a missing DNS level fails the prod plan immediately rather than producing a
   half-configured listener.

5. **The deploy roles may write records, never zones.** The role policy gains
   `route53:ChangeResourceRecordSets` scoped to `hostedzone/*`, the reads that
   Terraform needs, and read-only ACM. `route53:DeleteHostedZone` is absent
   deliberately: a role that could delete the zone could break the delegation
   from inside, and the repair lives in an account this project cannot reach.

6. **HTTPS is a property of prod, not a shared invariant.** The `alb` module
   takes an optional `certificate_arn`; `null` keeps exactly the previous
   HTTP-only behaviour. stage passes nothing. This is a deliberate difference
   between environments, and it is the reason it does not violate the
   "shared fixes go to every environment" rule adopted in Phase 9.0: the module
   change went to both, the instantiation differs on purpose.

The state-level model becomes seven:

```text
1. infra/bootstrap        S3 state bucket. LOCAL state. Permanent.
2. infra/bootstrap-oidc   OIDC provider + deploy roles. Permanent.
3. infra/shared-ecr       container registry. Permanent.              (ADR-0018)
4. infra/dns              hosted zone + certificate. Permanent.       (this ADR)
5. infra/public-site      dashboard S3+CloudFront. Permanent.         (Phase 11)
6. infra/envs/stage       workload. Destroyed every cycle.
7. infra/envs/prod        workload. Destroyed every cycle.
```

## Consequences

**One manual action, once, in an account this project otherwise never touches.**
The `NS` record for `demo.uveapp.net` is created by hand in the parent zone. It
is untracked state in a different trust domain — the same category as the GitHub
`prod` environment's protection rules, which git also cannot assert. Both are
recorded here precisely because nothing else can hold them. If prod's name ever
stops resolving, this record is the first thing to check.

**The blast radius stays inside the demo account.** No role in this project can
touch the parent zone, and no credential from the domain's account is needed
here. The delegation is one-way and revocable by deleting one record.

**A later transfer of the domain does not break anything**, as long as the
delegated zone and its `NS` record survive the move. That is the reason to
delegate now rather than wait for the transfer: nothing about this design has to
be redone afterwards.

**Cost:** one hosted zone, ~$0.50/month, permanent. ACM certificates are free.
The honest post-teardown statement becomes: after a teardown nothing bills beyond
the state bucket, the registry and one hosted zone — cents.

**`app.demo.uveapp.net` is a dead name most of the time**, because prod exists
only during a cycle (ADR-0017 D2a). The Phase 11 dashboard must say so rather
than link to it silently.

**The dashboard's certificate is a separate one.** CloudFront requires
certificates in `us-east-1`; this one is regional, in `us-west-2`, because an ALB
can only use a certificate from its own region. The wildcard here deliberately
does not cover the apex `demo.uveapp.net`, which is a CloudFront name in
Phase 11.

## Alternatives rejected

**Move the hosted zone for `uveapp.net` into the demo account.** Gives short
names (`app.uveapp.net`) and no extra zone. Rejected: it makes the whole domain
depend on the account this project treats as disposable, and anything else
already served from `uveapp.net` would have to be recreated there. Isolating the
demo is the point of the account model (ADR-0001); pulling the parent domain
into it inverts that.

**Cross-account access from Terraform.** A role in the domain's account, assumed
by the deploy role to write records. Rejected: the account is outside this
Organization, so the trust would also be cross-organization, and the OIDC deploy
role — whose selling point is that it is scoped to one demo account — would gain
standing authority somewhere else. More moving parts, worse story, no benefit
over one NS record.

**Manual records per cycle in the parent zone.** Rejected outright: the ALB name
changes every deploy, so this makes a human a required step in a cycle that is
supposed to have none.

**Certificate inside `infra/envs/prod`.** Rejected: re-validation on every cycle
adds minutes and a failure mode to the deploy path, for no benefit — the
certificate has no per-cycle content.
