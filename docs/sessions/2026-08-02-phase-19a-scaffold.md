# 2026-08-02 — Phase 19a: the self-service scaffold

**Written, validated statically, and NOT APPLIED.** No AWS API was called for
this phase. No deploy workflow was run; `ci.yml` ran on the push, as it does for
any commit, and was green in all four jobs. The button does not exist: the level that would
create it has never been applied, and the dashboard control that would press it
is hidden behind a flag pointing at an empty string.

The decisions were made ahead of the code in 19.0 (**ADR-0034**, **ADR-0035**),
which is why this session had nothing to decide and only something to write —
and why the two things it did discover are worth more than the code is.

## What was written

```text
infra/self-service/            the sixth permanent state level
  main.tf                      control store (one DynamoDB table, four kinds of
                               item), the secret CONTAINER, the SNS topic, the
                               deployment package
  launch.tf                    Function URL -> launch Lambda, and the narrow
                               callback role the workflow releases the lock with
  watchdog.tf                  EventBridge Scheduler -> watchdog Lambda, and
                               SNS -> kill-switch Lambda
  src/control.py               every refusal, and it imports no AWS SDK
  src/store_dynamodb.py        all the AWS knowledge, behind one interface
  src/github.py                App JWT -> installation token -> dispatch
  src/{launch,watchdog,killswitch}_handler.py
.github/workflows/self-service.yml
tests/unit/test_launch_refusals.py
make self-service-package
site/index.html                the button, behind a flag
```

Shared-invariant changes, which went to **stage and prod in the same commit**
even though nothing public can reach prod — the seven-week lesson:
`ExpiresAt` and `Launch` tags on both environments, and an optional SNS
subscriber on the budgets module so the kill switch has something to listen to.

## The finding: a guardrail that would have eaten its owner

ADR-0035 says a resource with a missing deadline is **expired, not exempt**.
Applied literally, that rule deletes the owner's own stage environment. An
owner-run cycle carries no deadline — and no deadline is exactly what "a human
is watching this one" looks like. The watchdog would have found a live stage
environment with no `ExpiresAt`, followed the rule it was given, and been right
by the letter of the ADR while destroying a cycle somebody was in the middle of.

The rule is not wrong; its SCOPE was unstated. ADR-0035 already says the
guardrails "do not apply to the owner's own workflow_dispatch runs", and this is
what that sentence costs in code:

```text
Launch tag   empty for an owner cycle, set to the launch id by the public
             launch workflow. The watchdog acts only on resources whose Launch
             tag is present and NON-EMPTY. Inside that scope, a missing
             ExpiresAt is still expired - the rule survives intact where it was
             meant to apply.
```

It is enforced twice, because a filter in a handler is a claim and an IAM
condition is a fact:

```text
in code   observe() drops every resource without a Launch tag
in IAM    every delete is conditioned on Project, on Environment=stage, AND on
          aws:ResourceTag/Launch being present (Null=false) and not ""
```

The `Null` test is not redundant with the `StringNotEquals`: for a resource with
no `Launch` tag at all, a `StringNotEquals` condition evaluates TRUE. That is
the quiet default that turns a policy into decoration, and this project has a
name for it already — a check that cannot fail.

So prod is unreachable from the public path by IAM rather than by an input
(ADR-0034), and now the owner's stage is unreachable from the WATCHDOG by IAM
rather than by a filter. Neither guarantee depends on the handler being correct.

## The thing the plan did not know: the runtime ships no crypto

Minting a GitHub App installation token means signing an RS256 JWT, and the
Lambda Python runtime provides boto3 and nothing else this needs. That is a
build step the plan never mentioned, and three refusals came with it:

```text
make self-service-package   refuses when pip3 is missing, and refuses when
                            PyJWT did not land in the package
terraform                   a precondition refuses to apply a package under
                            500 KB
```

An empty zip deploys happily and fails at the first request, in a place nothing
is watching. `--platform manylinux2014_x86_64 --only-binary=:all:` because the
wheel has to match the Lambda runtime rather than the machine that built it: a
devbox-built cryptography imports fine on the devbox and dies in AWS with a
symbol error, which is the same "one definition, two hosts" shape that handed
the image scan `postgres:16`.

## Four break tests, fired here, before delivery

The refusal logic is in `control.py` precisely so this is possible without AWS.
Each break was made, the suite was run, and the file was restored from a copy
taken first — `git checkout` after a deliberate break discards whatever was
uncommitted, which this project has already paid for once.

```text
break                                          result
the store failure treated as zero launches     2 failed - including the test
                                               that says the refusal must name
                                               the STORE and not the cap
the kill switch read AFTER the nonce           1 failed (order is the assertion:
                                               a late kill switch spends a nonce)
the cap refusal keeps the lock it took         1 failed
a missing deadline read as NOT expired         1 failed
restored                                       21 passed
```

What these can NOT show, said here so a green suite is not mistaken for a proven
guardrail: whether DynamoDB's conditional expressions mean what
`store_dynamodb.py` thinks they mean. Every one of the five refusals is still
unproven against the real table. That is 19b, with the output kept.

## Validation, and the two things running it corrected

In the sandbox first (no terraform, no checkov, no Lambda-platform pip): 21
refusal tests passed, every handler compiled, `check-docs-references.py` and
`check-action-pins.py` clean, and the HCL aligned by hand plus an approximate
`terraform fmt` checker written for this session.

Then on the devbox, where two of those answers turned out to be wrong.

**`terraform fmt -check` was red, and the checker was the reason.** A multi-line
value ENDS the alignment group and is not part of the preceding one, so `sid`
before a multi-line `actions = [` stands alone, and so does `Version` before
`Statement = [{`. The sandbox checker aligned both to neighbours terraform does
not consider neighbours — so it measured an assumption about the tool rather
than the tool, which is the same shape as the break test that failed to break
and as the Compose command that answered differently on two hosts. Twelve lines,
whitespace only, confirmed by `git diff --ignore-all-space` being empty before
the fix was committed.

**Checkov found a tenth decision the skip list had not predicted.**
`CKV_AWS_297`, EventBridge Scheduler without a customer-managed key. Four CMK
skips were written from reading the resources and were right; the fifth was
invisible from the code, and the same arithmetic settles it — about $1/month to
encrypt a fixed instruction to invoke a named function every five minutes, which
is already public in this repository. That is the difference between a skip list
written and a skip list run.

```text
terraform fmt -check   clean, after the fix
make tf-validate       eight root levels, infra/self-service OK first time
make test-unit         28 passed = 7 access-log + 21 launch refusals
make iac-scan          290 passed, 0 failed, 56 skipped by decision
make docs-check        6 documents, 0 findings
make action-pins       43 references, all SHAs
ci.yml on push         green in all four jobs, run 30779260262
```

The ten new Checkov skips are decisions, not snoozes, and the loudest is
`CKV_AWS_258` — the Function URL's AuthType is NONE. That is the design: the
button is public, nothing authenticates the visitor, and the goal is not that
only the right people can press it but that it does not matter who does. A
scanner cannot see the five refusals or the reserved concurrency; it sees a
missing authorizer.

## What is deliberately still missing

The provider lock for the new level is NOT on this list: the first
`terraform init -backend=false` produced it during validation and it is
committed, exactly as the other seven levels' locks are.

```text
the GitHub App, its installation, its   19b. Out-of-git state, listed in
  private key                           docs/preflight-inventory.md beside the
                                        NS record and prod's protection rules
SELF_SERVICE_* repository variables     19b, from the level's outputs
the endpoint URL in site/index.html     19b. The flag stays false until there
                                        is a URL to put there
every one of the five break tests       19b (lock, cap, kill switch) and 19c
  against real infrastructure           (TTL, blunt teardown)
```

## Cost

**$0.** Nothing was applied and no AWS API was called.
