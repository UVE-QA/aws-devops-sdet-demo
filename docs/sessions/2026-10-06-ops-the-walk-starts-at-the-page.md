# Ops — the walk starts at the page

**2026-10-06**, on `next`.

The owner, looking at the picture: the interface should talk to the api, and
the picture does not show it. Every flow was read back from the code. `web` is
nginx serving files and nothing else; the interface's script, in the browser,
calls `/api/*` at the same address and the load balancer routes it - locally a
proxy file in Compose plays the balancer, which is why `web` looks like it
calls the `api` there. The rest held: the item and its event in one
transaction, the relay's `SKIP LOCKED`, at-least-once with both consumers
idempotent, the worker deleting only after it publishes, poison left for the
dead-letter queue and transient failures left for the next delivery.

Six findings were put to the owner; three taken. The manifest now says the
`web` part serves an interface that calls the `api` - refused unless the
interface file fetches an `api` path - and the walk starts with the page, then
the script's call, and closes on the next read carrying `item_processing`
(ADR-0104 D6): twelve steps. The interface shows each item's processing: by
whom and when, or waiting for the worker - filled in place every few seconds,
touching none of the markers the tests wait on - or not processed, past two
minutes; the last came from the local database, whose items made before the
worker existed would otherwise have waited forever. Left for a later word:
`item.deleted`, trimming the outbox, a cap on a row that never sends, an alarm
that tells someone.

Gates 33/33 on the devbox. The whole path watched locally: a new item waiting,
then processed by the worker ten seconds later, without a reload.

Then, on the merged page, the owner again: no answer from `web` on the picture,
and nothing saying what the interface is for. The interface became a box inside
the browser, its purpose read from the file's own fetch calls and methods - it
lists, adds, edits and deletes items - and its card lists every path it asks
for; `web`'s answer got its own arrow back to the browser, the call to the
`api` now starts at the interface and the `api`'s answer returns to it. Thirteen
steps. Gates 33/33.

Then: is anything on the picture live during a cycle? Nothing was, by D4. The
status files already carry what it would need - tasks running against desired,
messages waiting, dead-letter counts and the alarm - so it became a page-only
change (ADR-0104 D7): badges on the box edges while an environment is up and
current, a line saying which one and what is not as asked, a switch when both
stage and prod are up, and the design alone otherwise. Checked on the recorded
fixtures - one environment with a stopped worker and an alarm, two
environments, none - in both themes; the credentials arrows moved to the right
of Secrets Manager so the worker's badge has room. Gates green.
