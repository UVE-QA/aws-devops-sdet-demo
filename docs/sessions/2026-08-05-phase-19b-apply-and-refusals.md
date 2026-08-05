# 2026-08-05 — Phase 19b: the level applied, and every refusal it could show

**Applied, and the three break tests this phase owns all fired.** The sixth
permanent level exists in the account: 25 resources, a live public endpoint, and
a control store that five different refusals were driven through by hand. No
cycle was run, no environment was created, and nothing was deployed — which was
the point of splitting 19b out of 19c in the first place.

Two defects were found by applying, neither of which any static check in this
repository could have seen, and both of which had already passed
`make tf-validate`, `make iac-scan` and 21 in-process assertions in 19a. A third
was found by USING a guardrail rather than testing it.

## What was applied

```text
infra/self-service      25 resources: the control table, three Lambdas, the
                        Function URL, the EventBridge schedule, the SNS topic
                        and its kill-switch subscription, the secret container,
                        five roles and their policies, three log groups
GitHub App              created by hand, installed on one repository with
                        actions:read-write and metadata:read, private key pasted
                        into Secrets Manager by the owner
```

Cost of the level: about **$0.45/month**, permanent, dominated by the Secrets
Manager secret at $0.40. Everything else is cents: EventBridge Scheduler at 8,640
invocations a month, a PAY_PER_REQUEST table holding kilobytes, and three log
groups at 14 days. Nothing here is destroyed by a teardown, which is the whole
reason the level exists (ADR-0027's rule, sixth arrival).

## Finding 1 — a guardrail the account quota cannot satisfy

The first apply failed on all three Lambdas:

```text
InvalidParameterValueException: Specified ReservedConcurrentExecutions for
function decreases account's UnreservedConcurrentExecution below its minimum
value of [10].
```

This account's Lambda `Concurrent executions` quota is 10 — the default for a
new account — and a reservation may not take the unreserved pool below 10. At
that quota **no reservation of any size is possible, for any function**, so the
`reserved_concurrency = 2` that ADR-0034 called the bound on what an
unauthenticated endpoint can cost by itself simply could not be applied.

No quota increase was requested, deliberately. Three rarely-invoked functions do
not need one, and while the quota stays at 10 the ACCOUNT ceiling is itself the
bound — numerically weaker (roughly $3/day rather than $0.70/day under a
sustained flood of a handler that refuses in milliseconds) and stronger in one
respect: it is account-wide and nothing inside the account can raise it. The
reservations became variables defaulting to `-1`, with the decided numbers one
uncommented line away in `terraform.tfvars.example`.

Worth keeping: **only one of the three reservations was ever a guardrail.** The
launch function's bounded spend; the watchdog's and the kill switch's were
single-flight, a correctness property, and the watchdog's 120s timeout against
its 300s interval already means an overlap needs a failed invocation that
EventBridge Scheduler retries.

## Finding 2 — a public function URL takes two policy statements, and this had one

The applied URL answered every request with `403 Forbidden` — anonymous and
SigV4-signed alike — while `AuthType` read `NONE`, the function read `Active`,
and the resource policy held exactly the statement AWS documents as the default
for NONE. The function was never invoked: zero log streams against a watchdog
with one, counted in the same command.

The cause is a behaviour change dated **October 2025**, stated in the first line
of the page the error message itself links to: a function URL now requires
`lambda:InvokeFunctionUrl` **and** `lambda:InvokeFunction`. The Terraform
provider creates the first statement on its own when `authorization_type` is
`NONE`, and does not create the second — so the missing half is the half nobody
wrote, and the configuration and the account disagree with nothing in between to
say why.

The fix needed provider `~> 6.0` on this level alone. `invoked_via_function_url`
does not exist in the v5 schema; the API rejects `FunctionUrlAuthType` on
`InvokeFunction` ("only supported for lambda:InvokeFunctionUrl"); and the one
v5-expressible alternative — `InvokeFunction` to `"*"` with no condition — would
let any AWS principal invoke the function directly, bypassing the URL and every
guardrail in ADR-0035. Provider 6.57.1 introduced **zero** drift on this level:
the plan after the upgrade was `1 to add, 0 to change, 0 to destroy`.

### Two dead ends, recorded because each looked like the answer

**An organization policy.** An account-wide refusal has an obvious suspect, and
the first check used `DescribeOrganization`'s `AvailablePolicyTypes` — a field
AWS documents as deprecated and incomplete. It listed only SCPs, which cannot
deny an anonymous request, so the hypothesis was closed on evidence that could
not carry it. `list-roots` from the management account settled it properly:
`SERVICE_CONTROL_POLICY` enabled, **no RCPs in the organization at all**, and the
only custom SCP is `Deny-IAM-IdentityCenter-Instance`, attached nowhere near this
account.

**A throwaway function.** A second Lambda with its own URL was created to
separate "this function is broken" from "function URLs do not work in this
account". It was refused identically, which read as proof of the latter — and
was worthless, because its permission had been added by hand with the same
single statement. **A control that reproduces the defect is not a control.** It
is the 15a lesson (a break test that fails to break tests your assumption about
the tool) arriving from the other direction.

## Finding 3 — the kill switch has no way back, and says only one thing

Found by using the control rather than testing it. Nothing in the repository
turns the kill switch OFF: there is no `disengage` in `control.py`, no `make`
target, and no line in ADR-0035 or any README. The way back is
`aws dynamodb delete-item` on one key, and until this session that command
existed nowhere.

Its refusal message is also coupled to one cause — it states that the budget
alarm has fired. Parking the endpoint by hand at the end of this session
therefore makes it tell visitors something untrue, while the honest reason sits
in the store where nobody sees it. Both are recorded in
`infra/self-service/README.md`; the message is a one-line fix and belongs with
19c, which touches that path anyway.

## The refusals, seen

```text
not_configured    503   before the App existed. Reaching it PROVES the store was
                        read: the kill switch is evaluated first
kill_switch       503   published the shape AWS Budgets really sends, subject and
                        all; the refusal CHANGED from not_configured, the reason
                        was stored verbatim, and deleting the item restored the
                        previous refusal - so the switch releases rather than
                        sticking
store_unavailable 503   the launch role's inline policy removed. BOTH halves
                        refused and both named the store: `issue_nonce` on the
                        GET, `get_flag(killswitch)` on the POST. Restored by
                        `terraform apply`, verified by the refusal changing back
locked            409   a seeded lock. The refusal NAMES the holder and its
                        run_url, and `gh run list` showed no run queued for
                        self-service.yml - with a positive control in the same
                        command, because an unauthenticated `gh` prints an empty
                        list that looks exactly like a clean queue
daily_cap         429   the counter seeded at 3 for the UTC day. Two assertions,
                        not one: the refusal, AND `lock -> null` afterwards,
                        because the cap is evaluated after the lock is taken and
                        a refusal that kept it would wedge the button until its
                        deadline
```

The day key was taken from `date -u +%F` rather than typed, so the test measured
the guardrail instead of the author's arithmetic.

## What this phase could NOT prove, and why

```text
lock takeover        an expired lock MAY be taken over. Proving it ends in a
                     dispatch, which is a real cycle - 19c
TTL (guardrail 3)    needs a run to cancel
watchdog blunt path  needs an environment to tear down
budget -> topic      TF_VAR_budget_topic_arns is now set on the stage and prod
                     environments, so the alarm will publish where the kill
                     switch listens. WIRED, NOT VERIFIED: nothing confirms it
                     until a deploy applies the budget module again
```

## Also this session

`make iac-scan` reddened `ci` on `main` the moment the second policy statement
landed: `CKV_AWS_301`, Lambda publicly accessible. The interesting part is that
the scanner had called this function private up to that point — the
`InvokeFunctionUrl` half is created by the provider and is invisible to Checkov,
so **the resource that fixed the endpoint is also the first thing that ever made
its public grant scannable.**

It became this repository's first INLINE skip, against the stated convention of
keeping all skips in `.checkov.yaml`. The convention names its own price — a
repository-wide skip lets a NEW violating resource pass silently — and "a Lambda
is publicly accessible" is the one alarm this phase least wants disabled
everywhere. `.checkov.yaml` records that the exception exists, so the readable
list does not lie by omission, and `make iac-scan` reports `1 skipped inline` on
its own line.

`docs/preflight-inventory.md` said `AdministratorAccess` was assigned to
`admin-temp` on the demo account. It is assigned on the management account too,
which is how the organization was inspected at all; the document was corrected,
along with the manual steps for a fresh account, which had not grown the
self-service level or the GitHub App.

## The state the account is left in

**Parked.** The endpoint is public, configured and would launch — so the kill
switch was engaged by hand, with a reason that says in words that this is not a
budget event. The URL appears nowhere public: the dashboard control is still
behind its flag. 19c starts by clearing that one item.

```text
lock                  absent
count#<day>           absent
killswitch            engaged, reason recorded, by hand
launch endpoint       503 kill_switch to everyone
```

## A question the owner raised twice, and deferred on purpose

Whether the button should be anonymous at all. ADR-0034 says the design goal is
"not that only the right people can press it, but that it does not matter who
does", and the owner asked directly whether a stranger should be able to spend
his money — proposing instead an emailed request he approves by hand, or an
on/off window he opens when a recruiter asks.

The decision was **deferred, not made**: build as designed, then decide. It is
recorded here rather than in an ADR because nothing changed. If it is taken up,
the cheapest form is inverting the default of the kill switch that already
exists — a window with a deadline the code compares against, never a DynamoDB
TTL, whose deletion is best-effort and can lag by up to 48 hours.

## Cost

**About $0.45/month standing**, from this session onward, plus a few cents of
Lambda and log ingestion. No environment was created, no cycle was run, and the
per-cycle cost of this phase was **$0**.
