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

**D5. The picture answers back (2026-10-05, on the owner's word).** Three
ways in, and none of them knows the geometry. Pointing at a step lights its
arrows and the boxes at their ends and dims the rest; *Follow one request*
walks the ten steps in order, a dot running along each arrow (not with
reduced motion); a box opens a card with what it is - a table's columns and
who writes and reads it, a queue's event and its contract's fields, a part's
class and file, a service's image, port, health and suites - with links to
the exact lines on GitHub. All of it is generated beside the picture from the
same sources: which arrows a step speaks of, the columns from the model or,
where there is none, the migration, the line each link points at. A class that
moves or a column that is added reddens `app-flow-check` until the picture is
regenerated, as a renamed table already did. And the picture is found: the header carries a
link to it on every part, drawn as the one thing in that row to press, and an
address ending in `#app-flow-cut` opens it - the owner's point being that a
stranger who does not know it is behind a cut in Details never gets there.

**D6. The walk starts at the page and ends at the next read (2026-10-06).**
The owner read the picture as saying the interface never reaches the api, and
it did say that by leaving it out: the walk began at "the browser asks".
`web` never calls the `api` - the browser does, from the interface `web`
serves. So the manifest says it: the `web` part names its `interface` and
that it `calls` the `api`, and the generator refuses the claim unless the
interface file fetches one of the `api`'s paths. The walk now starts with the
page and then the script's call, and it closes on the table the answering part
reads and another part writes - `item_processing`, which is how the worker's
half reaches the visitor. The interface shows that half too: each item says
when and by whom it was processed, or that it is waiting, filled in place while
it waits, or that it was not processed when two minutes have passed.
Then the owner again: the answer from `web` and what the interface is for were
still not on the picture. So the interface is drawn as a box of its own inside
the browser, and its purpose is read from the interface file - the paths it
fetches and the methods it uses, `lists, adds, edits and deletes items` - not
written by hand; `web`'s answer is an arrow of its own back to the browser; the
call to the `api` starts at the interface and the `api`'s answer returns to it.
Thirteen steps.

**D7. The picture during a cycle (2026-10-06, on the owner's yes).** D4 kept
the picture to structure, and the structure is still all it draws. But while
an environment is up and its reading is current, the counts the estate already
reads from the status files are laid on the boxes they belong to: tasks running
against desired on each service, messages waiting on each queue, the
dead-letter counts and the alarm's state in the dead-letter box, with a line
above saying which environment, when it was observed, and what is not as
asked. Nothing new is fetched or collected: the picture listens to the
observation the page's main script already hands out, and it decides nothing
about `up` or `stale` on its own. Which reading belongs to which box is
generated - a service's `status_key` from the manifest, a queue's key from the
observation script - and a queue the script does not observe is a refusal. The
lab is left out: its runtime is another picture. With nothing up, or an
environment being built or torn down, the picture says so and shows the
design.

## Consequences

- A fourth service, a renamed table, a new queue or a part that starts writing
  someone else's data reddens a gate before it reaches the page; proven on
  copies of the tree - a service consuming `results` with no place, a place
  for a queue that does not exist, a receipt that stopped being idempotent,
  the worker writing the api's table, a renamed table, a renamed class.
- The layout is still placed by hand. A service added for real needs its
  places written, which the refusal says; automatic layout is not attempted.
- `scripts/draw-app-flow.py` and `assets/app-flow.svg` are gone.
- (D5) The cards link to line numbers, so an edit that only moves code also
  asks for a regenerated picture; that is the price of links that cannot point
  at the wrong line.
