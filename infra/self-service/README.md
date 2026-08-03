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

Written in 19a and **not applied**. Nothing in this directory has run.
Every refusal it makes is proven in 19b and 19c, or the button does not become
public - see `docs/next-phases.md`.
