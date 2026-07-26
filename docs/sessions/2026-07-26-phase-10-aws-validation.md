# Session 2026-07-26 — Phase 10 closed: the AWS validation cycle

Phase 10 was code complete and green locally before this session started, and
that is exactly the state the cursor refused to call done. This session ran the
one thing that decides it: a full `deploy-stage -> promote-prod -> destroy both`
cycle through GitHub Actions, with no manual AWS operation.

## What ran

```text
deploy-stage  30218469484   14m54s   green, FIRST attempt
promote-prod  30219504665   13m31s   green, paused for required reviewers
destroy prod  30221241572    8m24s   green, paused for required reviewers
destroy stage 30221612424    8m29s   green
```

All four from `main` at `1bf89ac`, the commit this session read its state from.

Both new AWS-facing steps passed on their first run against stage: the API
contract suite against the ALB, and `Assert the UI write reached RDS` — an ECS
task carrying an environment override, the genuinely new AWS path this phase
introduced. The phase-gate note predicted one failed run for it, on the grounds
that every new path in this project so far has cost exactly one. It did not.
The prediction is recorded as wrong rather than quietly dropped; the reasoning
behind it was sound and remains the right default.

`promote-prod` stopped before its first step with `prod waiting for review`, so
the approval gate was demonstrated in the system that enforces it. The AWS half
(`trust_branch_ref = false`) was never reached — GitHub refused earlier.

## What the cycle established

The closing criteria, each against the environment that decides it:

```text
regression green in ci.yml against Compose      met in the previous session
read-only smoke green against deployed prod     met (--project=smoke only)
DB assertion proving a UI action reached RDS    met, in stage, by a process
                                                other than the browser
destroy passes end-to-end at the end of the     met, both environments
  phase, not only at the end of the MVP
```

Prod was then checked from outside the workflow that had just declared itself
green, with a different tool, from a different host:

```text
health 200 ssl=0            certificate verified by curl, not by a workflow step
redirect 301                HTTP -> HTTPS
/api/items 200              seed-item-001, description: null
```

That last line is the one worth keeping. `/api/items` did not exist before this
phase, and `description` arrived with Alembic revision 0002 — so the response
proves prod was running the Phase 10 slice on a database migrated to 0002, not
an older image that returns 200 for `/health` and nothing else.

The UI write path against prod was then exercised by hand, deliberately, because
nothing automated covers it: prod runs the read-only suite only, by design. A row
created through the browser appeared as `id=3`. That path is now known to work in
prod, and it is known by the only method available — a human doing it once per
cycle. Worth stating plainly at interview rather than implying the suites cover
it.

## The incident: prod looked dead for half an hour and was not

Immediately after promotion the browser showed `API health: unreachable`,
`DB check: unreachable` and `could not load items`, then `Safari Can't Find the
Server`. Three symptoms, one cause, and the cause was not in AWS.

The sequence that found it:

```text
gh run list --workflow=destroy.yml     no teardown had been started
curl health / items from the devbox    200, 200 — prod was serving throughout
curl POST from the devbox              201, so the write path was not broken
dig from the macbook                   resolved, both system and 1.1.1.1
dig NS uveapp.net @a.gtld-servers.net  delegation correct, authoritative zone
curl from the macbook                  could not resolve host
```

`dig` resolved and `curl` on the same machine did not, because `dig` queries a
nameserver directly while `curl` goes through the macOS system resolver. The
resolver was holding a **negative** cache entry: `app.demo.uveapp.net` had been a
dead name for hours while prod was destroyed, and the laptop remembered. A cache
flush fixed it, and the browser then showed the live page.

This is not an incidental annoyance. Per ADR-0017 D2a the prod name is dead most
of the time by design, so any client that touched it before a promotion can keep
reporting "no such server" for some time after prod is up and healthy. At an
interview that is indistinguishable from a broken demo. The operational rule:
**verify prod with a request that bypasses the system resolver, and flush the
resolver cache before showing anything.**

```bash
sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder
```

The wider lesson is the project's oldest one in a new costume. Three independent
client-side symptoms all pointed at the application, and the application was
never involved. A claim about state — including a browser's — is not state.

## Findings in the repository, fixed here

**`aws sso login` needs `--use-device-code` on the devbox, and the repository
said so in exactly one place.** The requirement was documented in
`docs/preflight-inventory.md` and in the 9.1 session summary, while eight other
locations still printed the flagless form: `docs/phase-gates.md`,
`infra/bootstrap/README.md`, `docs/project-prompt.md` (three times),
`docs/decisions/0002`, and the `deploy-stage`, `tf-workflow` and `teardown`
skills. A session that copied from any of those got the broken form. All now
carry the flag. Documenting a trap once does not remove it while the wrong
command is still copyable from eight files — the same shape as
"`promote-prod.yml` said read-only and ran everything".

**A verification that lost its credentials reads as a clean account.** The first
attempt at the post-teardown check ran with an expired SSO token and printed nine
empty lines — `ecs :`, `rds :`, `alb :` and so on — which is precisely what a
correct teardown looks like. Only the interleaved stderr gave it away. The check
was rerun with `aws sts get-caller-identity` as its first statement and each
result assigned to a variable under `set -e`, so a credential failure aborts
instead of rendering as green. The teardown skill now carries that shape.

**The `teardown` skill still expected the ECR repository to disappear.** Since
ADR-0018 the registry is a permanent level, so the skill would have told a future
session that a correct teardown had failed. It also still said the OIDC
provider's fate was undecided and "document which choice this repo made", seven
weeks after ADR-0015 made it. Both fixed, and the skill now lists all four
permanent levels that a destroy must not touch.

## Post-teardown state, verified against the AWS CLI

```text
account   993912191738
ecs rds alb nat eks eip vpc logs secrets     all empty
ecr       aws-devops-sdet-demo-app           permanent, ADR-0018
zones     demo.uveapp.net.                   permanent, ADR-0024
buckets   aws-devops-sdet-demo-tfstate-...   permanent
```

Nothing billable remains. Both `destroy` runs also passed their own
environment-scoped verification step, but that is the workflow checking itself;
the table above is the independent check the invariant asks for.

## What is NOT done

- No new ADR came out of this session. Nothing structural was decided — the
  findings are a documentation defect, a verification defect and a stale skill.
- The gitleaks full-history sweep is still owed, and the contradiction about it
  between `docs/next-phases.md` 11.0 and `docs/discussion-log.md` is still
  unresolved. Carried forward again, now noted twice.
- `tests/db/assert_seed.py` and `app/scripts/assert_seed.py` remain two copies of
  one assertion.
- Three actions still annotate as Node 20 deprecated on every run.
- The stray `demo` NS record in the non-authoritative copy of the parent zone
  (account 478937318617) is still there.

## This session edited docs/session-primer.md

Two entries were added to "Verification habits" (an empty result is not a clean
result; documenting a trap once does not remove it) and three to "Known traps"
(the client-side negative DNS cache, and `--use-device-code` as an explicit step
rather than a footnote). **The local copy at
`~/Projects/_claude-transfer/session-primer.md` must be refreshed after this is
pushed**, or the next session starts from a stale entry point:

```bash
scp devbox:aws-devops-sdet-demo/docs/session-primer.md ~/Projects/_claude-transfer/
```
