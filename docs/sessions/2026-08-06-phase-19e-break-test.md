# 2026-08-06 — Phase 19e: the break test

## Done
- publish-site was dispatch-only, so the site ran 20h behind main. Added a push
  trigger limited to site/**, plus concurrency; exception recorded in
  docs/security-posture.md. Verified by a real push, not by reading.
- Break test: launch ss-a9a983b4c9662b08 started through the public endpoint
  and cancelled mid-apply (ALB created, RDS creating).
- ADR-0036 D1/D2/D3 all confirmed on live evidence.
- Found and fixed -target=module.alb (commit f1ed545); wrote ADR-0037.

## Timeline (UTC)
    01:35 cancelled; 01:38 stale state lock broken by preflight in 6s
    01:52 "Destroy ALB first" fails 15m22s, DependencyViolation on alb-sg
    01:52 release-lock keeps the lock (destroy=failure)
    03:01 watchdog writes pk=watchdog and dispatches destroy
    03:17 RDS and ALB gone, watchdog record cleared
    then  four manual AWS calls to empty the rest

## True now
- account empty, destroy green including the verification step
- teardown reclaims the BILLABLE resources with no human; the remainder can
  still need manual calls until ADR-0037 D2-D4 ship

## Next
19f = ADR-0037 D2-D4, then repeat this break test. Done when a cancelled
launch needs ZERO manual AWS calls.

## Gotchas
- gh run view --log returned nothing for several runs; the API path
  repos/:owner/:repo/actions/jobs/<id>/logs worked every time
- devbox clock is UTC, the GitHub UI shows PDT (-7). State times in UTC
- a long watch belongs in nohup: SSH dropped three times during the test
