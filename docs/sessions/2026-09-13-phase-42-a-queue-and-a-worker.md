# Phase 42 — A queue and a worker

**2026-09-13**, the same session that closed Phase 41, continued.
**ADR-0096**, one record, nine decisions, verified by one cycle.

Item 2 of the plan, discussed before it was written and built in three
slices that were each green on their own: the application and the worker
with a local queue; the infrastructure and the pipeline; the page. One cycle
from `next` proved the three together, and `main` is `next` again.

## What was decided, and by whom

The owner's four words settled the four questions that mattered:

> processed_at ок, прямая публикация с дырой, alarm без action, ElasticMQ ок

So the worker's mark is on the api's own row — the shared-database debt plan
item 4 pays, taken knowingly so that this step's story is the asynchronous
seam and that one's is data ownership. The api publishes directly after the
commit, and the gap between the two writes is named in `src/events.py` rather
than closed by an outbox nobody has a home for yet. The alarm on the
dead-letter queue has no action, because there is nobody to page and an
action bound to nothing is the appearance of one. ElasticMQ stands in for SQS
on the devbox with the same two queues and the same redrive, so the code has
no local branch — an endpoint URL and nothing else.

## What the worker is

A third service that listens on nothing and answers nobody. `POST /api/items`
commits, answers 201, then publishes `item.created`; the worker long-polls,
runs one statement — `UPDATE … SET processed_at = now(), processed_by = ?
WHERE id = ? AND processed_at IS NULL` — and deletes the message. The
statement is idempotent by construction, so at-least-once delivery costs
nothing. A message it can never act on is *poison*: logged with the reason
and **left**, so SQS carries it to the dead-letter queue after three receipts;
deleting it would make a dead-letter queue that can never fill. A transient
failure is left too, for the opposite reason. No port, so the health check
is a heartbeat file the loop touches on every pass. Its own image, its own
package, none of the api's code; the two share a message contract, and the
unit suite runs the api's own message builder through the worker's parser.

The work it does is nothing, on purpose: the application is boring so the
machinery can be the subject, and what the machinery produces is a fact a
client can observe — two nulls turning into values after the 201 — which is
the whole of the two new contract tests, waiting on a deadline and never a
sleep.

## What the first run found

**Two contract tests raced the worker.** Whole-row comparisons — *GET returns
the item*, *a refused PATCH leaves the row untouched* — failed because the
worker's stamp landed between two reads. They compare the fields the api owns
now; the suite's first lesson in eventual consistency, learned on the second
run of the day.

**`scripts/queue.py` shadowed the standard library.** The break test's helper,
run as `python scripts/queue.py`, put its own directory first on `sys.path`,
and urllib3 underneath boto3 imported it as `queue` and died on
`queue.LifoQueue`. It is `sqs_tool.py`.

**SQS ARNs have no kind.** `arn:aws:sqs:…:name` is the one shape whose
resource part is a bare name; `arns.py` would have read the queue's name as
its kind and matched no rule. It calls the kind `queue` now; the sweep
confirms one by `get-queue-url`, the adoption imports one by its URL.

**Checkov wanted encryption.** Both queues took the SQS-owned key — free, no
KMS — because the rule was one this project agrees with.

**The plan band kept tiles for things the board already drew.** ADR-0095 had
left `web` and `api` greyed on *What comes next* beside the real tiles on the
estate; the queue and the worker would have made that four. A tile leaves the
band the day the board draws the thing.

## The cycle

```text
#26  34762487475  14:22  success   62 m — launch 17, promote 13, destroy 11,
                                   hold 5, destroy-prod 12, release-lock
```

After `infra/shared-ecr` (2 added: the worker's repository) and
`infra/bootstrap-oidc` (2 changed: six ECS roles and `sqs:*`) were applied
under `demo-admin` with the owner's yes — once refused by an expired SSO
session and applied on the second try. The worker image built in 12 s; three
services stable in 62 s; the asynchronous tests green against the ALB, which
is a Fargate task consuming events and stamping rows; both environments
observed while up as `worker ACTIVE 1/1` and `queue: 0 waiting, 0
dead-lettered, alarm OK`; promotion pinned three digests, and the pointer
went from ADR-0095's two names — reported *not armed*, as D7 says — to
`{api, web, worker}` in one put; both teardowns green, the sweep confirming
six roles and asking the queues by name; afterwards no cluster, instance,
balancer, queue, alarm or role in the account.

## What the owner found watching the page

During the cycle: *stage is up and the button is open — what happens if
someone presses it?* The button was open because the tab was older than the
merge that fixed it (ADR-0093 D2, amended that morning); a hard reload
closes it. But the question underneath is real and is recorded as open in
ADR-0096: the endpoint's lock sees only launches that came through the
button, so a visitor's press during an owner-run or `next` cycle is accepted,
spends one of the day's three, and queues behind it on the workflow's
`concurrency` group. Harmless — nothing runs twice — and not the refusal
ADR-0036 wrote. The fix is the endpoint asking Actions for in-flight runs
before it dispatches.

Also asked and answered along the way: what SQS is beside MQTT (a queue with
an HTTP API, point-to-point, no protocol and no topics; SNS is the pub/sub
half, IoT Core the MQTT one), and what a dead-letter queue is for (the third
outcome for a message that fails: neither lost nor cycling, but kept where
it can be read, fixed and redriven — and, with an alarm on it, a sensor: an
empty one is the proof that everything that arrived was processed).

## The merge

`main` fast-forwarded to `next` on the owner's *да, вливай*: four commits,
the whole of Phase 42. The estate is 163 resource blocks, 60 permanent and
103 per cycle; the release is three digests; the suites count 196 tests.

## Postscript: the endpoint learns to ask

Taken the same evening, first on the owner's *продолжаем по порядку*. The
lock in the control store is written and read by the endpoint alone; a cycle
dispatched from Actions holds none, so the refusal ADR-0035 wrote for *one at
a time* was, for such cycles, GitHub's queue. The endpoint now asks the
Actions API for unfinished runs of the workflow from any branch — after the
nonce, so a bad press costs no GitHub call, and before the lock, so a press
during a lockless cycle never takes one — and refuses `409 busy` naming the
run and its branch. An API that cannot answer is `503 github`, fail-closed:
a dispatch to it would fail a moment later anyway. The lock stays beside it
for the seconds between a dispatch and the run's appearance in the API.
Three refusal tests in process; one package, three Lambdas, one apply.

## What is still open

The outbox, with plan item 4. The services manifest of item 5, which now
has four lists of service names to reconcile: the module instances, the
adoption rules, the deploy role, and every workflow. From before: the
*being torn down* tense for a `next` teardown, the lab site, the two blunted
break tests, the release-tag 403 of 2026-09-05.
