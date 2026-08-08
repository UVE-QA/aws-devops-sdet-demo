# ADR-0041: A free leftover is found from the configuration, not from a scan

## Status
Accepted (Ops session, 2026-08-08). Extends ADR-0037 D4 with a second discovery
channel and ADR-0038 D3 with a kind nothing discovers. Does not amend the
watchdog (ADR-0035, ADR-0036); see D6.

## Context
The first apply after 2026-08-05 failed before it started anything interesting:

```text
EntityAlreadyExists: Role with name aws-devops-sdet-demo-stage-ecs-task
  already exists     module.ecs.aws_iam_role.task   (and .execution)
```

Both roles existed in AWS and in no Terraform state. They were created at
2026-08-05T05:44:49Z by an anonymous self-service launch — they carry
`Launch=ss-a5af40dd40861808` — and they survived that launch's teardown, three
subsequent sessions about teardown correctness, and 19g's uninterrupted cycle.
Every `deploy-stage` failed at the ECS module for three days.

**They survived a teardown that verified itself GREEN, because that verification
asks whether any BILLABLE resource remains and an IAM role is free.** So the
gate could not see the class of leftover that breaks the next apply, and neither
could anything else: `sweep-orphans.sh` reported `verdict: clean, exit 0` against
this account on 2026-08-08 while both roles were alive. That was reproduced on
demand, in seconds, at no cost, before any of this was written.

The reason is not that the sweep is wrong about anything. Its confirmation stage
is fail-closed and would have reported an IAM role as `unconfirmed` — red — had
one ever reached it. **Nothing ever did.** Three explanations were possible and
two were eliminated:

```text
not the region   `get-resources` in us-east-1 answers, and answers WITH IAM:
                 it returns arn:aws:iam::…:oidc-provider/token.actions.githubusercontent.com
not the tags     `iam get-role` shows Project, Environment, Owner, ManagedBy,
                 ExpiresAt and Launch on both roles
what remains     iam:role is not in the tagging API's index. iam:oidc-provider is.
```

**The control was inside the same answer, which is why this conclusion is worth
something.** The OIDC provider and the two permanent `github-deploy` roles live
in the same state level, carry the same `Project` tag, and were asked for in the
same call; the provider comes back and no role does. The one thing that differs
is the resource type. Building a separate control — a second query in another
region — would have produced an empty result to interpret, and this project has
already recorded where that leads (ADR-0037's amendment; the 403 control that
reproduced its own defect in 19b).

## Decision

### D1. The class is a NAME COLLISION, not a free resource
`docs/next-phases.md` framed the question as "which free resources may be left
behind at all". That framing does not survive contact: deregistered
task-definition revisions are free and are left behind for ever, deliberately,
because `terraform destroy` cannot delete one and nothing can run from one. A
predicate of "free" therefore needs an exception list, and an exception list is
what the tags let this repository avoid everywhere else.

What actually broke is precise: a resource whose DETERMINISTIC NAME the next
apply will need. That is the class, and `EntityAlreadyExists` is its symptom.

Checked rather than assumed, for the other IAM resources in the same module: an
inline `aws_iam_role_policy` and an `aws_iam_role_policy_attachment` cannot
collide, because `PutRolePolicy` and `AttachRolePolicy` are idempotent. The roles
themselves are the only members of the class here.

### D2. Discovery is the gap; confirmation was never wrong
No change to the fail-closed rule in `confirm_exists`, no change to the
precedence in `decide_sweep`. What is added is a channel that brings ARNs the
tagging API cannot.

### D3. The second channel asks the CONFIGURATION, not the account
For kinds the tagging API does not index, the names to look for come from
`adopt_orphans.RULES` — the map that already says what this configuration has —
via `unindexed_names`. The sweep then asks the owning service whether each name
is there. `iam:role` is the only such kind today.

A prefix scan (`iam list-roles` + `list-role-tags`, filtered on
`Environment=<env>`) was designed first and rejected on two counts, the first of
which makes it unrunnable:

```text
permissions   the deploy role has iam:GetRole on exactly the two role ARNs, and
              neither iam:ListRoles (which is account-wide, Resource: *) nor
              iam:ListRoleTags. A scan needs a NEW account-wide grant applied to
              a PERMANENT state level — in order to build a gate. The
              configuration-driven channel needs no grant at all: GetRole on
              those two ARNs is already there
noise         a scan reports every project-prefixed role, including one somebody
              created by hand. That reddens every teardown for ever, and a red
              destroy keeps the lock (ADR-0036 D2), so the public button would
              stay shut after every launch. A gate that is always red is
              switched off, and this one takes the button with it
```

Two properties fall out that a scan would not have had. The permanent
`<prefix>-github-deploy` role can never be reported, and not because a tag says
so — it is not in the environment's configuration at all, so nothing asks about
it. And the exclusion of hand-made roles is deliberate rather than accidental:
this gate exists to unblock the next apply, and the next apply only collides
with names the configuration will create.

### D4. One control per channel, and the only arm that separates two failures
`decide_sweep` takes named controls and refuses if ANY channel is empty, naming
which. A single shared control was right with one channel and is exactly wrong
with two: the loud channel would vouch for the silent one, which is this gate's
own failure mode rebuilt inside the gate.

```text
tagging-api        the permanent levels are always tagged, so empty means the
                   question was not answered
configured-names   the configuration always declares at least one such name, so
                   empty means the declaration went missing
```

And `iam:role` is the first arm in `confirm_exists` to distinguish "it is gone"
from "I could not ask". Every other arm treats any failed `describe` as absent,
which is safe there for a reason that does not hold here: the tagging API had
already proved the credential works by returning the ARN. This channel touches
no AWS during discovery, so nothing is proved, and an `AccessDenied` would
otherwise read exactly like a role that is not there.

### D5. Adoption gets the kind AND what hangs off it
`RULES["iam:role"]` maps `ecs-task` and `ecs-execution` to
`module.ecs.aws_iam_role.task` and `.execution`; Terraform imports a role by
name. `test_every_address_exists_in_the_configuration` covers the new addresses
for free. The reverse direction is new and is the one that matters here:
`test_every_role_in_the_configuration_is_declared` fails if a module gains an
`aws_iam_role` with no entry in the map — because in this channel the map is the
QUESTION, so a gap in it is a resource nobody will ever ask about, invisible
exactly the way the first two were.

**Amended before this ADR was pushed, by the live specimen.** The first version
of D5 adopted the role and nothing else, and that would have been worse than
adopting nothing. `DeleteRole` REFUSES while any policy is attached or inline,
and AWS was asked what was attached before anything was removed:

```text
…-ecs-task        bare
…-ecs-execution   attached  AmazonECSTaskExecutionRolePolicy
                  inline    aws-devops-sdet-demo-stage-read-db-secret
```

So the teardown that leaked these roles leaked FOUR objects, not two. Importing
only the role hands the following `terraform destroy` a `DeleteConflict`: a RED
teardown that leaks the role anyway, and a red destroy keeps the launch lock
(ADR-0036 D2), so the public button would shut after every such run. Turning
"green and leaking" into "red and still leaking" is a worse gate, not a stricter
one.

**The usual partial-failure shape hides this completely**, which is what makes it
worth writing down rather than just fixing. When an apply COMPLETED, the
attachment and the inline policy are in state beside the role, and `destroy`
removes them first; importing the role alone is then perfectly correct. It is
wrong in exactly the shape that produces orphan roles in the first place — role
and policies in AWS, nothing at all in state — which is the shape that will
recur.

`DEPENDENTS` therefore maps a parent ADDRESS to the imports that must accompany
it, and Terraform does the ordering from the configuration's own graph, which is
ADR-0038's thesis one level deeper. Appended AFTER the duplicate check: a parent
that lost its address has nothing for its dependents to hang off.

`force_detach_policies = true` was the shorter alternative and is not used. It is
a provider-side flag with no field behind it in AWS, so an imported role carries
its default `false` in state, and `destroy.yml` imports and destroys with no
apply in between — relying on it means relying on provider internals nobody here
has tested, which is the definition of a break test measuring an assumption
about the tool.

`test_every_policy_on_a_mapped_role_is_declared_a_dependent` is the drift gate
for this half: a policy attached to a mapped role and not declared is a
`DeleteConflict` waiting for the next cancelled apply.

### D6. The watchdog is unchanged, and that is a decision rather than an omission
`observe()` in `infra/self-service/src/watchdog_handler.py` looks at ECS
services, load balancers and RDS instances. Its job is to stop the meter inside
a TTL, and a free leftover does not tick; widening it would put a fourth API
call in a function that runs every five minutes to find something that costs
nothing per minute. The teardown's own gates are the right owner.

Recorded because it is adjacent and will look like a gap later: `deadline_passed`
in that Lambda already reads `ExpiresAt`, so the general predicate — nothing
whose own tag says it expired may still exist — is present in this repository,
applied to a three-kind observation. Both roles carried
`ExpiresAt=2026-08-05T07:10:39Z` and stood for three days. That is a candidate
second gate, deliberately not built here.

## Consequences
- `sweep-orphans.sh` has two discovery channels and prints them separately. A
  single list would hide which question found what, and the finding is that one
  of the two questions was not being asked.
- `sweep_orphans.py --declared` is REQUIRED. A channel that can be omitted from
  a call silently is a channel that will be; the old command line, unchanged,
  answered `clean`.
- The merged answer is `discovered.json`. `adopt-orphans.sh` reads it rather than
  `tagged.json`, or it would refuse to import exactly the orphan the second
  channel exists to find.
- Both environments are covered by one script; there is no per-environment copy
  to keep in step.
- The break test was not planted. Two real orphans, created by an anonymous
  public launch and unnoticed for three days, were still in the account when the
  gate was built, so the gate was reddened on an unplanted specimen and only then
  was the account cleaned. The planted case stays in `tests/unit` so the gate
  keeps being exercised once the specimen is gone.
- The three-day survival is itself the finding worth carrying: a resource whose
  own tag said it had expired outlived a teardown, three sessions about teardown
  correctness, and a cycle nobody interrupted. Everything green throughout.
