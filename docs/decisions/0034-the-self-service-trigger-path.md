# ADR-0034: The self-service trigger is a Lambda Function URL and a GitHub App, at a permanent level

## Status
Accepted (Phase 19a, 2026-08-02). Implements ADR-0017 D4 Wave B. Recorded
BEFORE the implementation, like ADR-0029 and ADR-0031, because the decision it
makes is the one that is expensive to reverse. Depends on ADR-0022 (the
repository is public), ADR-0026 (what each source may assert) and ADR-0027 (what
must outlive a teardown).

## Context

Wave A gave anyone with the link the ability to LOOK. Wave B gives them the
ability to SPEND, which is a different kind of decision and the reason it was
scheduled last.

Everything built so far rests on one direction of trust: **GitHub authenticates
to AWS through OIDC, and no static AWS key exists anywhere.** A button on a
static page reverses the direction — something has to authenticate to GitHub, on
behalf of a visitor who has no account — and there is no OIDC in that direction.
A browser cannot hold that credential, and a static site has nothing that can
refuse a request.

So the question is not whether a long-lived GitHub credential enters this
project. It does, in this phase, and pretending otherwise would be the kind of
claim this repository keeps catching itself making. The question is **which
credential, where it is kept, and how long a token minted from it is valid.**

The second thing the context has to say is who is at the other end. Nothing here
can establish that. A public page with a public endpoint is pressed by whoever
finds it, including a script that found it in the page source. The design goal
is therefore not "only the right people can press it" — it is:

```text
it does not matter who presses it.
```

The cost bound has to hold under an adversary, not under a polite visitor. That
bound is ADR-0035's subject. This ADR only has to guarantee that the path it
builds can be refused, entirely, at a single point that the visitor does not
control.

## Decision

### One endpoint, at its own permanent level

```text
infra/self-service/    key self-service/terraform.tfstate, same bucket
                       applied LOCALLY under demo-admin
                       never referenced by destroy.yml
```

**Its own level rather than an extension of `infra/public-site`.** Different
blast radius — this is the one level that holds a long-lived GitHub credential —
and a different lifecycle: a fresh account can have the dashboard without Wave B
at all, and changing a rate limit must not re-apply the distribution that serves
the public face of the project.

**Permanent, and this is the sixth arrival at ADR-0027's rule.** Everything the
endpoint uses to REFUSE — the in-flight lock, the day counter, the kill switch —
is state about the cycle. A control that lives inside the environment it
controls is destroyed by the thing it is controlling, which is the same sentence
as the registry (ADR-0018), the hosted zone (ADR-0024), the dashboard
(ADR-0027), the release pointer (ADR-0029) and the alarm's notification channel
(ADR-0032), reached this time from a spend control rather than from an artifact,
a name or a pointer.

**A Function URL rather than API Gateway.** One route, no authorizer to
configure, no custom domain requirement. API Gateway would add a resource whose
only contribution here is a nicer hostname. Reserved concurrency on the function
bounds what an unauthenticated endpoint can cost by itself, independently of
everything in ADR-0035.

### The credential: a GitHub App, its private key in Secrets Manager

The Lambda reads the App's private key from Secrets Manager, mints an
installation token, calls the dispatch endpoint, and discards the token.
Installation tokens expire in one hour and carry exactly one permission,
`actions: write`, on exactly one installation.

Rejected: a fine-grained personal access token. It is a USER credential —
everything it does is attributed to a person, its expiry is a calendar date
rather than an hour, and revoking it revokes it everywhere that person used it.
The App's private key is then the only long-lived secret in the project, it
lives in one place Terraform never prints, and rotating it is one paste.

**What this costs the security story, stated rather than discovered at
interview.** The claim was "no static keys anywhere". It becomes:

```text
no static AWS keys anywhere, and exactly one static GitHub credential,
held in AWS Secrets Manager in the demo account, readable by one Lambda
execution role and by nothing else.
```

Every document that states the short version needs the qualifier. That is a
Consequence below, not a footnote, because the short version is currently a
talking point.

### `workflow_dispatch`, and the run has to name itself

The Lambda dispatches a workflow — `.github/workflows/self-service.yml`, new in
19a — and does nothing else. `repository_dispatch` is rejected: it requires
`contents: write`, strictly wider than the one thing this needs, and its payload
never appears in the run's UI.

The lesson ADR-0026 already paid for applies unchanged: the anonymous Actions
API does not expose `workflow_dispatch` inputs, so a run must carry in its NAME
whatever an outside reader needs.

```yaml
run-name: self-service launch ${{ inputs.launch_id }}
```

Without it the dashboard — the only source allowed to talk about runs — cannot
tell a visitor that the run they are watching is the run they started.

### The public path targets stage. It cannot reach prod.

prod has the approval gate in both halves (`trust_branch_ref = false` in IAM and
the environment's protection rules in GitHub), the release pointer, the rollback
and the public name. A stranger's button must not reach it.

The guarantee is IAM, not an input that happens to say `stage`: the self-service
workflow resolves the stage deploy role only and declares no prod environment,
so there is no value of any input that produces a prod credential.

### The nonce is a speed bump, and is labelled as one

The page fetches a short-lived single-use token before it can POST. Two honest
purposes: a trivially scripted loop against the endpoint fails, and each launch
gets an id the dashboard can display.

It is **not** authorization. Whoever can read the page can get one. Writing that
down is the point — this project has twice mistaken a claim for an observation,
and a nonce presented as access control would be the third.

A CAPTCHA (Turnstile or similar) is rejected for v1: a third-party dependency in
the one path meant to demonstrate AWS, bought for a guarantee the guardrails
have to make anyway. If abuse is ever observed it is a small addition — but if
the cost bound NEEDS it, the cost bound is wrong.

### What lives outside git

Same category as the NS delegation in the parent zone and prod's protection
rules — real state that git cannot assert:

```text
the GitHub App itself, and its permission set
its installation on UVE-QA/aws-devops-sdet-demo
the private key, pasted by hand into the Secrets Manager secret
```

Terraform creates the secret CONTAINER and the role that reads it. It must never
hold the key. If a launch ever returns 401, check these three before anything
else.

## What this deliberately does not do

```text
- it does not authenticate the visitor, and does not pretend to
- it does not let the public path reach prod
- it does not let the Lambda touch infrastructure. It dispatches a workflow;
  every AWS mutation still happens under the existing stage deploy role,
  through OIDC, exactly as it does today
- it does not put the public endpoint behind the Lightsail devbox, for the
  reason the dashboard is not there either: the public face of the project
  must not depend on the machine used to develop it
```

## Consequences

- One more permanent level to apply on a fresh account.
  `docs/preflight-inventory.md` ordering grows by one step, after
  `infra/public-site`.
- One manual, out-of-git setup step, documented beside the NS record and the
  protection rules rather than in a place of its own.
- `README.md`, `docs/architecture.md` and `docs/interview-talking-points.md`
  state "no static keys". They need the qualifier above. It is a BETTER talking
  point with it: the interesting part is that the one static credential is held
  where it can be scoped, rotated and audited, not that none exists.
- The dashboard gains a control and not only a view. ADR-0026's rule is
  unchanged: the page's report of a launch still comes from the runs API and
  `status.json`, never from the Lambda's own answer.
- Cost of the level: a Lambda invoked a handful of times a day, one Secrets
  Manager secret at $0.40/month, and a small amount of state. Cents, fixed,
  permanent — the same trade ADR-0027 made.
- Nothing in this path can be proven by reading it. Every refusal it makes has
  to be broken on purpose before the button is public: ADR-0035.
