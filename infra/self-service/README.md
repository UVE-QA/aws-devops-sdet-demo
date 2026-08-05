# infra/self-service

The button, and everything it uses to refuse. Permanent level (ADR-0027's rule,
sixth arrival), applied locally under `demo-admin`, never touched by
`destroy.yml`.

Read `docs/decisions/0034-the-self-service-trigger-path.md` and
`docs/decisions/0035-launch-guardrails-and-where-the-watchdog-lives.md` first.
They are the reasoning; this is the wiring.

```text
launch.tf      Function URL -> launch Lambda -> workflow_dispatch (stage only)
               plus the narrow callback role the workflow releases the lock with
watchdog.tf    EventBridge Scheduler -> watchdog Lambda (out-of-band TTL),
               and the SNS topic -> kill-switch Lambda the budget alarm flips
main.tf        the control store, the secret CONTAINER, the deployment package
src/           the handlers. The refusal logic is in control.py, which imports
               no AWS SDK, so tests/unit can exercise every refusal in-process
```

## Before the first apply

```bash
make self-service-package
```

PyJWT and cryptography are not in the Lambda Python runtime, and minting a
GitHub App installation token means signing an RS256 JWT. The apply has a
precondition on the package size: an empty archive is what a forgotten build
step looks like, and Lambda accepts one happily.

## The account quota this level cannot satisfy

`reserved_concurrent_executions` is `-1` on all three functions, and the
decided numbers (2, 1, 1) are commented in `terraform.tfvars.example`. AWS
refuses any reservation while the account's Lambda `Concurrent executions`
quota is 10, since the unreserved pool may not fall below 10. Found by applying
in 19b; amended in ADR-0034. The account ceiling is the bound meanwhile.

## Turning the kill switch OFF

There is no target, no handler and no other command: the way back is one
`delete-item`, and until Phase 19b it was written down nowhere. Engaging is
automated (the budget alarm publishes, a Lambda flips the flag); disengaging is
a decision, so it is manual - but manual and UNDOCUMENTED are different things,
and it was the second one.

```bash
aws dynamodb delete-item \
  --table-name aws-devops-sdet-demo-self-service-control \
  --key '{"pk":{"S":"killswitch"}}' \
  --profile demo-admin --region us-west-2
```

Read it before deleting it - the item carries the `reason` it was engaged with,
and that is the only place the honest cause is recorded:

```bash
aws dynamodb get-item \
  --table-name aws-devops-sdet-demo-self-service-control \
  --key '{"pk":{"S":"killswitch"}}' \
  --profile demo-admin --region us-west-2
```

**The refusal message names the budget alarm whatever engaged the switch.** It
is a fixed string in `control.py`, so an endpoint parked by hand tells visitors
something untrue while the honest reason sits in the store where nobody looks.
Known, one line to fix, and it belongs with 19c.

## What is NOT in git, and never will be

Same category as the NS delegation in the parent zone and prod's protection
rules - real state Terraform cannot assert:

```text
the GitHub App itself, and its permission set (actions: write, one repo)
its installation on UVE-QA/aws-devops-sdet-demo
the private key, pasted by hand into the secret this level creates
```

If a launch ever returns 401, check those three before anything else.

## Status

**Applied 2026-08-05 (Phase 19b), and parked.** Everything here exists in the
account. The endpoint is public and configured, and it currently refuses every
request because the kill switch was engaged BY HAND at the end of that session -
an armed public button with nobody watching had no reason to stay armed. 19c
starts by clearing that item, with the command above.

Proven against the real table in 19b: the kill switch, the store-unavailable
refusal on both halves, the lock (naming its holder, with nothing queued), and
the daily cap (with the lock released afterwards). Not proven, because each ends
in a real cycle: the takeover of an expired lock, the TTL, and the watchdog's
blunt path. Those are 19c.

This level needs provider `~> 6.0` and is the only one that does - see the
comment in `main.tf`.
