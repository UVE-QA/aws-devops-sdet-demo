# 2026-08-08 — Ops: the gate that sees a free leftover

The teardown finding from 20b.2, closed. Two IAM roles that survived a green
teardown and blocked every `deploy-stage` for three days are gone, and the
teardown can now see the class of leftover they belong to. **ADR-0041.** Under
$0.01 of real money — one workflow run, no resource created.

Not a phase, deliberately. The cursor had assigned this finding to nobody, and
Phase 19 was declared finished hours earlier; `19h` was proposed, questioned, and
withdrawn rather than reopen a phase a document had just closed.

## What this session established

**A gate can be green on a non-empty account, and this one was — reproducibly, in
seconds, for free.** Before any code was written, `scripts/sweep-orphans.sh
stage` was run against the live account and said `verdict: clean, exit 0` while
both roles were alive. That run became the control for everything after it: 90
minutes later the same command in the same account said `orphans, exit 1`, and
the only thing that had changed was the code. Both halves are in
`docs/sessions/2026-08-08-ops-live-break-test.log`.

**The break test was never planted.** The specimen was real, created by an
anonymous public launch, and unnoticed for three days — so the order of work was
inverted on purpose: build the gate, redden it on what was already there, and
only then clean up. Deleting the roles first would have thrown away the only
unplanted specimen this defect has produced.

## Why nothing could see them

```text
free            the teardown's gate asks whether any BILLABLE resource remains,
                and an IAM role is free. Green, and the account was not empty
not in state    a partially failed teardown drops resources out of state, so
                Terraform does not mention them either
not indexed     the Resource Groups Tagging API does not index iam:role, so the
                sweep - which discovers through it - was never handed one
```

The sweep's own confirmation stage was blameless: it is fail-closed and would
have reported an IAM role as `unconfirmed`, which is red. Nothing ever reached
it.

**The control was inside the same answer, which is the part worth carrying.**
Three explanations were possible and two were killed by one command:
`get-resources` in us-east-1 answers, and answers WITH IAM — it returns the
`token.actions.githubusercontent.com` OIDC provider — while returning no role at
all, though the two permanent `github-deploy` roles carry the same tags, live in
the same state level and were asked for in the same call. The one thing that
differs is the resource type. Building a separate control in another region would
have produced an empty result to interpret, and this repository has a standing
record of where that leads.

## The fix, and the design it forced

Discovery inverts: for kinds nothing indexes, the names come from the
CONFIGURATION, because a name collision can only happen on a name the
configuration will create. `adopt_orphans.unindexed_names` reads the map that
already says what this environment has, and the sweep asks the owning service
about each name.

A prefix scan was designed first, approved, and then found **unrunnable** by
reading the deploy role's policy before writing code: it holds `iam:GetRole` on
exactly two ARNs and neither `iam:ListRoles` (account-wide, `Resource: *`) nor
`iam:ListRoleTags`. Scanning would have needed a new account-wide grant applied
to a PERMANENT state level in order to build a gate. It would also have reported
hand-made roles for ever, and a red destroy keeps the launch lock (ADR-0036 D2),
so the public button would shut after every run.

Two properties fell out that the scan would not have had: the permanent
`<prefix>-github-deploy` role can never be reported, and not because a tag says
so — it is not in the environment's configuration at all.

**One control per channel now.** A shared control would have the loud channel
vouch for the silent one, which is this gate's own failure mode rebuilt inside
it. And `iam:role` is the first arm in `confirm_exists` to tell "it is gone" from
"I could not ask": every other arm treats a failed `describe` as absent, which is
safe only because the tagging API had already proved the credential by returning
the ARN. This channel touches no AWS during discovery, so `AccessDenied` would
otherwise read exactly like a role that is not there.

## The defect this session put into its own patch, and how it was caught

Patch 1 adopted the orphan role and nothing else. **That would have been worse
than adopting nothing**, and it was caught by asking AWS what was attached BEFORE
removing anything:

```text
…-ecs-task        bare
…-ecs-execution   attached  AmazonECSTaskExecutionRolePolicy
                  inline    aws-devops-sdet-demo-stage-read-db-secret
```

`DeleteRole` refuses while a policy is attached. So the import would have handed
`terraform destroy` a `DeleteConflict` — a RED teardown that leaks the role
anyway, with the launch lock kept and the button shut. Green-and-leaking would
have become red-and-still-leaking.

**The usual shape hides it completely.** When an apply COMPLETED, the attachment
and the inline policy are in state beside the role and `destroy` removes them
first; importing the role alone is then correct. It is wrong in exactly the shape
that orphans a role — role and policies in AWS, nothing in state — which is the
shape that recurs. Patch 1 was applied on the devbox and deliberately NOT pushed
until patch 2 fixed it.

`force_detach_policies = true` was shorter and rejected: it is provider-side with
no AWS field behind it, so an imported role carries its default `false` in state
and `destroy.yml` imports and destroys with no apply in between. Relying on it is
relying on provider internals nobody here has tested.

## Validation

Offline first, in the chat's own sandbox, on fixtures, before any account was
touched:

```text
role present and unmanaged   verdict: orphans   exit 1
role absent                  verdict: clean     exit 0     control, both sides
declaration empty            verdict: refuse    exit 1     named the channel
```

Then on the devbox: `make test-unit` 112 green, `make docs-check`,
`make site-data-check`, `make site-page-check`, and `ci` green on `4d95caa`
(all four jobs).

Then the live cycle — `destroy.yml` for stage, every step green, which is exactly
the shape that has fooled this project before, so the verdict came from the AWS
CLI:

```text
sweep in the workflow   verdict: orphans, both roles — under the deploy role's
                        OIDC credential, so the grants were sufficient as they were
adoption                adopted 4 of 4; 0 could not be imported
terraform destroy       removed them in dependency order; no DeleteConflict
sweep at the end        verdict: clean
aws iam get-role        gone, gone            <- the actual verdict
```

## Two things found on the way, both fixed here

**CI went red on `site-data-check`** for the ADR this session added: the map
publishes how many decisions the repository has, and 41 stopped being true. The
gate did its job on the first commit that gave it the chance. Its MESSAGE did
not — it named `infra/` and `tests/`, where nothing had changed, and the drift
was in `docs/decisions/`. It now names every source it reads.

**A measurement measured the wrong thing.** `gh run list -L 1` returned the
`publish-site` run, so `ci exit: 0` was about a different workflow entirely. Same
family as the layout check that measured the document instead of the box: the
answer was true and the question was not the one being asked. Re-measured with
`-w ci` and the head SHA printed beside it.

## Chat session links are no longer published

Six commits from 2026-08-08 carry a `Claude-Session: https://claude.ai/code/…`
trailer, and this repository is public. Checked rather than assumed: the URL
resolves only for the account that owns the session — the strongest evidence
being a bug report in the Claude Code tracker that argues for removing the
trailer and still concedes "requires authentication to access". Not a credential,
so the six stay: rewriting them would change 32 SHAs and falsify a line in a
recorded break-test log.

`.claude/settings.json` sets `attribution.sessionUrl: false`, project scope, so
every session on the devbox inherits it — configuration rather than a rule to
remember. **The key is undocumented and is NOT yet proven:** this session's
commits arrived by `git am` from the chat, where the trailer never appears, so
they cannot demonstrate anything. The first commit from a Claude Code session on
the devbox is the test.

## Also worth knowing, found while looking

**The MacBook's default AWS credential answers for the wrong account.** No
`demo-admin` profile exists there, but the default one resolves to
`arn:aws:iam::478937318617:user/AdminCLI` — the unrelated `vlad.urban.qa` account
outside the Organization, already known for holding a look-alike hosted zone.
`iam get-role` asked from the Mac would have returned `NoSuchEntity` for both
roles, which reads exactly like "the orphans are gone". Every AWS question in
this session went through the devbox under `demo-admin`, with the account id
printed first.

**The TTL is written onto the resource and nothing reads it afterwards.** Both
roles carried `ExpiresAt=2026-08-05T07:10:39Z` and stood for three days. The
watchdog's `deadline_passed` already implements that predicate, applied to a
three-kind observation. Recorded as a candidate second gate in
`docs/next-phases.md`, not built (ADR-0041 D6).

**The tagging API's lag was visible in one afternoon**, which is a live
demonstration of the comment that has been in `sweep-orphans.sh` since 19f: the
environment query returned 26 ARNs at 17:50 and 24 at 19:20, and the project-wide
control 49 then 47, with nothing applied in between.

## Cost
One `destroy.yml` run and a handful of read-only AWS calls. No resource created,
IAM deletions are free. Under $0.01.
