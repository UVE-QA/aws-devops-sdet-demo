# Ops — the button's cycle after the plan, and the commits nobody counted

**2026-09-16 and 2026-09-18**, on `main` through `next`, docs only. No code
changed; one cycle from the button.

## The commits nobody counted (2026-09-16)

The owner's GitHub profile showed no activity from this repository, ever:
ten author addresses over 496 commits, none of them verified on the
account (the record is in the Phase 47 session). The owner verified the
two iCloud relays; GitHub linked the commits within the hour
(`contributors`: UVE-QA 345) but did not recount the profile's graph. A
commit pushed to `main` with the account's own noreply address - this
repository's local `user.email` since 2026-09-15 - was counted at once;
the 345 older ones were not, after more than a day. The text for a GitHub
Support request is in the conversation, to be sent from the owner's
account if the graph stays as it is.

## #37 from the button (2026-09-18)

*lets start full cycle to refresh data on dashboard.* Pressed by the owner
from a private window at 14:03 UTC on `main` `09f5e14`; watched from the
devbox as a visitor would see it. Green end to end in 66 m 45 s: launch
21 m, promote 16 m, lab 21 m, destroy 12 m, destroy-lab 13 m, hold 5 m,
destroy-prod 11 m, release-lock. On the page: no banner, the button closed
on the bucket's pulse, the first snapshot 12 seconds after the press, zero
GitHub requests; at the 22nd minute stage `measured` - 1/1 running on api,
web and worker, both queues empty; three `destroyed` after; the hook's
`completed` 13 seconds after `release-lock`. The owner, at the 14th
minute, on tiles that said `created` and nothing more: *all fires but not
starts yet* - which is the design, the apply stream's word until the
launch job observes at its end; explained, not changed.

## One finding

The bucket's snapshot holds the forty newest runs of `main` regardless of
workflow, and since 2026-09-14 those are 18 CI, 10 dependabot and 9
publisher runs: three lifecycle runs are left in the window, so the
history reads *1 of 3 failed* over a span of days and will read worse as
CI runs accumulate. `publish-runs.sh` should list the four lifecycle
workflows rather than the newest forty; a hand dispatch of `publish-runs`
proves it without a cycle. Proposed, and taken the same day - *давай, чини
окно истории в publish-runs*.

## The window, fixed

`publish-runs.sh` asks for the runs of each lifecycle workflow by name,
merges them newest first and cuts at forty (ADR-0100 D1 amended). Run from
the devbox against the real API before any merge: 40 lifecycle runs of
`main` reaching back to 2026-08-09 where the bucket held three, 33 green,
7 not, the same 111 KB. The four names now live in three places - the
page's `WRITERS`, the hook's trigger, the script - and a new
`lifecycle-list-check` holds them together; before it was wired it refused
a `destroy` forgotten in the script and a `sweep` invented in the hook.
Proven after the merge by a hand dispatch of `publish-runs` for #37.
