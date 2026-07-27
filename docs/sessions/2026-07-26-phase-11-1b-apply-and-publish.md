# Session — 2026-07-26 — Phase 11.1b: apply the public site, and write the publishing

/ driver: chat session, executing on the devbox /

## What this step was for

11.1a wrote `infra/public-site` and applied nothing. 11.1b is the first billable
step of the phase and was deliberately kept alone, so that the decision to spend
money stood on its own and could be reviewed as a plan rather than as a side
effect of building a page.

## The apply

Plan reviewed before anything was created: **16 to add, 0 to change, 0 to
destroy**, matching the scaffold exactly — 4 bucket resources, certificate and
its validation, distribution and OAC, 6 Route53 records, role and role policy.

```text
apply    16 added, 0 changed, 0 destroyed. First attempt. ~4 minutes.
         CloudFront distribution 2m32s of it; the certificate validated in 1s
         once the two DNS records existed.
```

Outputs, all identifiers rather than secrets:

```text
site_bucket_name           aws-devops-sdet-demo-site-993912191738
distribution_id            ED562RSB6XC49
distribution_domain_name   d1nj4thkcagijn.cloudfront.net
certificate_arn            arn:aws:acm:us-east-1:993912191738:certificate/00cb8629-...
publish_role_arn           arn:aws:iam::993912191738:role/aws-devops-sdet-demo-site-publish
site_url                   https://demo.uveapp.net
```

## Verification, and why 403 was the result to want

Checked against the AWS CLI and `curl`, never against Terraform state, with
`aws sts get-caller-identity` first and every value assigned under `set -e`
inside a `bash -c` — the Phase 10 trap where an expired token prints empty lists
that look exactly like a clean account.

```text
distribution   Status Deployed, Enabled true, both aliases, OAC attached
bucket         all four public-access-block flags true
certificate    ISSUED, InUseBy the distribution
dns            demo.uveapp.net resolved AUTHORITATIVELY to four CloudFront IPs
http           403 on the CloudFront domain, on the apex and on www,
               ssl_verify_result=0 on all three
```

A 403 with a verified certificate is the honest state of an empty private bucket
behind OAC: TLS terminates, CloudFront reaches the origin, and the origin has no
object to return. **A 200 there would have been the alarming result** — it would
have meant something was serving content nobody had uploaded. Doing this check
before any content existed is what separates "the hosting works" from "the page
looks right", two failures that are indistinguishable once index.html is in place.

## What came free

- Both data sources resolved at **plan** time: `aws_route53_zone` and
  `aws_iam_openid_connect_provider`. That is a proof that `infra/dns` and
  `infra/bootstrap-oidc` are applied, obtained without querying either and
  before anything billable was created. Had one been missing, the plan would
  have failed — the ordering is expressed as an error rather than as a comment.
- `infra/public-site/.terraform.lock.hcl` was **untracked**, and diffing it
  against another level showed it one `h1:` hash short. The 11.1a `tf-validate`
  run had written it without ever installing the provider; the real `init`
  completed it. Committed here, so the seventh level pins its provider like the
  other six.

## Two wrong predictions, kept

The project's standing default is that a genuinely new AWS path costs one failed
run, and 11.1a additionally budgeted a correction round for HCL written without a
local `terraform fmt`. Neither happened: the plan was clean and the apply was
green first time. Recorded rather than deleted, exactly as Phase 10's identical
miss was — the reasoning stays the right default even when the outcome is better
than it predicts.

## The publishing, written and not yet run

Everything below exists in git and has never executed. That distinction is the
point of writing it down.

```text
site/index.html                    placeholder. States that it reports nothing
                                   about stage or prod, because neither source
                                   exists in the bucket yet.
scripts/observe-environment.sh     DEPLOY role. Reads ECS/ALB/RDS and prints
                                   JSON. Every unread field is null.
scripts/publish-status.sh          PUBLISH role. Adds the run's own facts,
                                   writes status/<env>.json, publishes the
                                   Playwright report, invalidates what changed.
scripts/publish-site.sh            PUBLISH role. Syncs site/ and invalidates.
.github/workflows/publish-site.yml dispatch-only, environment: stage.
deploy-stage / promote-prod /      two steps appended to each, both if: always()
  destroy
```

Three design points worth defending out loud:

**Two roles inside one job.** The observation needs the deploy role's reads; the
upload needs only the publish role, which can touch this bucket and this
distribution and nothing else. A role that can change infrastructure does not
write the page that reports on it. The cost is that the publish steps must be
last, because re-configuring credentials takes the deploy role away from every
step after them.

**One status file per environment, not one shared `status.json`.** ADR-0026's
wording implies a single file; concurrency says otherwise. Destroying prod while
stage deploys is a normal cycle here, and a shared file needs read-modify-write
against S3, which has no compare-and-set — the second writer would silently drop
the first's block. Two keys have no race to lose, and each one then has exactly
one writer, which strengthens the ADR's rule rather than bending it. Noted in the
ADR itself so the code cannot quietly contradict it.

**`--exclude` in the site sync is load-bearing.** `aws s3 sync --delete` from
`site/` would delete `status/` and every published report — a step called
"publish the site" removing the evidence the site exists to show. That is this
project's recurring failure shape (a command doing something its name denies), so
the exclusions carry a comment saying so.

`if: always()` on both new steps: a run that died half way is exactly when the
environment is in a state nobody predicted. A status file that appeared only
after success would report the account as it was the last time things went well.

## What was still owed to close 11.1b (all met, see Validation below)

```text
1. four repository variables: SITE_BUCKET, SITE_DISTRIBUTION_ID,
   SITE_PUBLISH_ROLE_ARN, SITE_URL   (UI state, by hand, values above)
2. publish-site green, with https://demo.uveapp.net/ returning 200 asserted BY
   THE WORKFLOW rather than eyeballed
3. that run printing the PUBLISH role from get-caller-identity, because the
   scoping is the exhibit and an exhibit should be asserted
```

The status steps in the three lifecycle workflows are excluded from that list on
purpose: only a real cycle exercises them, and that is 11.1c.

## Documents that had to move with the apply

- the `teardown` skill now lists **five** permanent levels, and says so with the
  count, because a stale list here makes a correct teardown look failed. Held
  back until now on purpose: a document must not describe as existing in AWS
  something that exists only in git.
- `docs/preflight-inventory.md` gains `infra/public-site` as step 6 of the
  per-account apply order, plus the four repository variables.
- `docs/session-primer.md` no longer calls the level "not built yet", and its
  DNS trap now distinguishes the two kinds of name: the apex and `www` are always
  up, only `app.` is expected to be dead between cycles.

## Validation — what running it actually showed

`publish-site` 30227614075, dispatched from `main`, **green on the first attempt
in 18 seconds** (2026-07-27 00:31 UTC). Both assertions were read out of the
run's log, not claimed afterwards:

```text
identity   arn:aws:sts::993912191738:assumed-role/
           aws-devops-sdet-demo-site-publish/GitHubActions
http       attempt 1: 200 — https://demo.uveapp.net/ over a verified TLS chain
sync       index.html, 4.3 KiB, then invalidation I50M4NEKBIXSE8W2MFSIB337X4 /*
```

The identity line is the exhibit of this whole level: a page published by a
credential that cannot touch infrastructure. It is printed inside the run
because "the role is narrow" is a claim, and the ARN is an observation.

### The exclusion guard, seen both green and red

A guard that has only ever been seen working is indistinguishable from one that
cannot fail, so this one was made to demonstrate both halves — and the second
half was free:

```text
canary placed at status/canary.json and reports/canary/index.html,
  then publish-site re-run       -> both survived, index.html re-uploaded
same sync WITHOUT the excludes   -> (dryrun) delete: reports/canary/index.html
                                    (dryrun) delete: status/canary.json
same sync WITH the excludes      -> nothing
```

So the danger was real: a step named "publish the site" would have deleted every
environment status file and every published Playwright report. Four gates in this
project have now been shown red on purpose; this is the fourth.

## The tag divergence this session created and then closed

`infra/public-site` went out with `Owner=uve` while the other six levels carry
`Owner=UVE`. The lowercase form came from `terraform.tfvars.example`, written in
11.1a and copied here without question — a shared literal treated as an
independent knob, which is exactly the failure mode `variables.tf` warns about
two variables further down for `zone_name`.

It matters because a tag is not decoration: the `Owner` tag is what a cost or
ownership query filters on, so one level spelling it differently drops that level
out of every such query, and the query still looks like it worked.

```text
plan     0 to add, 6 to change, 0 to destroy
apply    0 added, 4 CHANGED, 0 destroyed
```

Six versus four is worth noting rather than smoothing over: two of them were
`aws_iam_policy_document` consumers that Terraform re-reads at apply time and
therefore cannot prove unchanged in advance. They were unchanged.

Verified afterwards on the resources themselves — `get-bucket-tagging`,
`list-tags-for-resource`, `list-role-tags` — all three now `UVE`.

And a third value surfaced: `docs/preflight-inventory.md` documented the Owner
tag as `papers.usher.3m@icloud.com`, which nothing in the account had ever been
tagged with. That is the budget alert address, recorded in the wrong section, and
it had been the written answer to "what is the Owner tag" for seven weeks.

## Cost

One bucket holding a 4 KB page, one CloudFront distribution on PriceClass_100, a
free ACM certificate, and six records in a zone that was already paid for. At
portfolio traffic this sits inside the CloudFront free tier, which is a tier and
not a guarantee: the figure to watch is requests, not storage. Permanent by
design — no destroy workflow touches this level.
