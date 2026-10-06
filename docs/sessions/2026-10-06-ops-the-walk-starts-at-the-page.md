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
