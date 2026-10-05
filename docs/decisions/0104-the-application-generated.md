# ADR-0104: The application, generated

## Status
Accepted (2026-10-04). **Supersedes ADR-0103** (the application, drawn); keeps
its D3 - a second cut in `Details`, closed until asked for. Extends **ADR-0101**'s
manifest with the inside of each service.

## Context

ADR-0103 put a hand-drawn picture of the application in `Details` and said so
on it; its consequences named the next step - a derived version, if the drawn
one earned its place. The owner asked for the plan, and answered its three
questions: the picture stays in `Details` and is whole without a cycle running
(*чтобы была возможность посмотреть схему апп даже при не запущенном цикле*);
whether to show tables and step numbers was left to judgement, *чтобы было
наглядно и не перегружало*.

## Decision

**D1. The manifest describes the inside.** `services.json` gains, per service,
`database.tables` and `parts` - each part `http` or `loop`, the file and the
class or function it is, and the tables and queues it reads and writes - and a
top-level `events`, each queue's contract in `contracts/`. `manifest-check`
holds all of it to the code in both directions: a table a model or migration
declares and the manifest does not give the service, a table the manifest gives
and no code declares, a part whose symbol its file does not define, a queue a
part uses that its service does not, a queue no part uses, a contract that does
not exist. And one rule ADR-0098 stated and nothing enforced: a part touching
a table its service does not own is a refusal.

**D2. The picture is generated; only its places are written.**
`scripts/generate-app-flow.py` derives every tile, arrow, number and sentence:
the steps are the walk from the browser through the routed service's request
part, what it writes, the loop that reads what was written, the queue it
publishes to, the part of another service that consumes it - until nothing new
is reached, numbered in the order met. The dead-letter count and its silent
alarm come from `infra/modules/queue`. A clause beyond the manifest - *a second
delivery changes nothing*, *only then does it delete the event*, *two replicas
never send the same row* - is a note in `assets/app-flow-layout.json` with the
file and the text that make it true, and is refused when the code stops saying
it. That file otherwise only places things, and the generator refuses a thing
with no place and a place with no thing. `app-flow-check` is the drift gate,
local, in the one list.

**D3. Tables by name, steps by number.** Each schema shows its tables by name
only - the point of the picture is that each service writes its own, and three
names say it; columns would not. The main path keeps its numbers 1-10, with the
same numbered sentences under the picture; the dead-letter and credential lines
carry none and are told apart by colour and dash.

**D4. Structure, not state.** The picture describes the repository, so it is
the same whether or not a cycle is up; what is running now stays the estate's
to show (ADR-0099).

## Consequences

- A fourth service, a renamed table, a new queue or a part that starts writing
  someone else's data reddens a gate before it reaches the page; proven on
  copies of the tree - a service consuming `results` with no place, a place
  for a queue that does not exist, a receipt that stopped being idempotent,
  the worker writing the api's table, a renamed table, a renamed class.
- The layout is still placed by hand. A service added for real needs its
  places written, which the refusal says; automatic layout is not attempted.
- `scripts/draw-app-flow.py` and `assets/app-flow.svg` are gone.
