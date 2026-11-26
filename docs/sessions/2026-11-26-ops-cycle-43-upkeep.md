# Ops — cycle #43, upkeep

**2026-11-02 and 2026-11-26**, on `next`, then `main`.

**The wildcard, renewed by hand.** `*.demo.uveapp.net` in ACM us-west-2, the
certificate the stage and prod load balancers use, was marked INELIGIBLE for
renewal with three months left. ACM renews only certificates that are in use,
and this one is attached to anything only while a cycle runs. The plan to
replace it was shown first - `infra/dns` is a permanent level - and applied on
the owner's yes: a new certificate requested, validated through the zone, the
old one removed; 3 added, 3 destroyed, no drift after. Prod's lookup takes the
most recent ISSUED certificate by name, so nothing else changed. The new one
expires 2027-05-18, and the same replacement will be due in April 2027.

**Five dependency updates.** Dependabot's open pull requests - the app's FastAPI
0.141 to 0.162 with SQLAlchemy, Alembic and boto3, Playwright 1.64, pytest and
SQLAlchemy in the test suites, three pinned Actions - had been green for weeks
against an older `main`. They were combined on a local branch over the current
`main` and the whole list run: 31 of 33 at first, the two reds the devbox's own
(a cached web image older than its base, a test venv older than the new pytest
pin); 33 of 33 once those were refreshed. Then each was merged into `next` on
its own, CI green after each, and `main` fast-forwarded.

**Cycle #43, from the button**, green in 66 minutes over those updates. It was
the first cycle on the renewed wildcard, and prod's HTTPS worked. On stage,
after its tests had passed, one item was created on the owner's yes to watch
the part the 2026-10-06 session had left open: the worker processed it and the
interface showed it 0.3 seconds after it was written - outbox, both queues,
the receipt, the projection, on AWS.
