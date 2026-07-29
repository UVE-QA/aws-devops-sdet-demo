# ADR-0031: The list endpoint paginates by default, and PATCH updates only what was sent

## Status
Accepted (Phase 16a). Extends the items contract of Phase 10, which deliberately
left room for this: `app/src/schemas.py` already said "Pagination is Phase 16;
adding `limit`/`offset`/`total` to an envelope is additive, whereas adding them
to a bare array is a breaking change to every consumer and every test written
against it."

## Context

Phase 16 asks for the rest of the CRUD surface — `GET` by id, `PATCH`,
pagination, and the full 404/422/409 matrix. Two of those are not additions but
contract decisions, and both have a wrong answer that only shows up later.

`GET /api/items` returns every row. With one seeded item that is invisible;
it is still an unbounded response whose size is decided by whoever last used
the create form. The envelope was built in Phase 10 precisely so that bounding
it later would not break its consumers.

`PATCH` has a well-known trap of its own: a partial update that cannot tell
"the client did not mention this field" from "the client sent null" either
silently wipes fields or makes it impossible to clear one. Which of the two it
does is decided by how the request model is written, not by the route body.

## Decision

### 1. The envelope gains `total`, `limit` and `offset`; `count` keeps its meaning

```json
{ "items": [ ... ], "count": 20, "total": 137, "limit": 20, "offset": 0 }
```

`count` is the number of items IN THIS RESPONSE, exactly as before, so the
Phase 10 assertion that `count` matches `len(items)` stays true and stays
meaningful. `total` is how many rows exist. Keeping both is what lets a client
render "20 of 137" without a second request, and it gives the suite a pair that
can disagree — a bug in the limit shows up as `count > limit`, a bug in the
count query shows up as `total < count`.

### 2. There is a DEFAULT limit, not only an optional one

```text
limit    default 20, minimum 1, maximum 100    -> 422 outside the range
offset   default 0,  minimum 0                 -> 422 below it
```

Pagination that only paginates when asked bounds nothing: the unbounded default
is the thing being fixed, and every existing client would keep the old
behaviour. The cap matters for the same reason — `?limit=1000000` is otherwise
the old endpoint with extra steps.

The bounds are declared on the query parameters, so the 422s come from the
framework's validation rather than from hand-written checks in the route.

### 3. The order stays ascending, and the UI moves instead

`ORDER BY id` ascending was chosen in Phase 10 so that position assertions mean
something. Paginating an ascending list has one consequence that must be handled
somewhere: **the newest item is on the LAST page, not the first**, so a create
form that reloads page 1 appears to do nothing as soon as there are more rows
than the limit.

Flipping to descending would fix the appearance and break the documented
ordering contract and every test written against it. Instead the UI jumps to
the page containing the new row after a create, and steps back a page when a
delete empties the current one. The API keeps one order; the client decides
what to look at.

This is the half that would not have been noticed until stage had accumulated
enough rows — which is to say, until some later session, on a path nobody was
looking at.

### 4. PATCH is partial, and absent is not the same as null

The request model is validated with `exclude_unset`, so only fields the client
actually sent are applied:

```text
{"description": "new"}   -> description changes, name untouched
{"description": null}    -> description is CLEARED, deliberately
{"name": null}           -> 422. name is NOT NULL; clearing it is not a thing
{}                       -> 422. an update that updates nothing is a mistake,
                            and answering 200 to it hides the mistake
unknown field            -> 422, from the same extra="forbid" as create
```

`{}` returning 422 rather than 200 is the one judgement call here. A no-op PATCH
is almost always a client bug — a form that sent the wrong key, a serialiser
that dropped a field — and 200 is the answer that makes it invisible.

### 5. A rename onto a taken name is 409, from the constraint

Same mechanism as create, for the same reason: the unique index decides, an
`IntegrityError` is caught and mapped. A `SELECT` to check first and an `UPDATE`
after is a race that answers 500 under concurrency. The comment in `create_item`
warned that a second constraint on the table would make that mapping ambiguous;
this change adds no constraint, so the mapping stays unambiguous.

### 6. `updated_at` exists, added by revision 0003

Without it, the database assertion after an edit through the browser can only
check that the name is different — which a replayed request or a stale read
could also produce. With it, the assertion can say the row was WRITTEN: the
name is the new one and `updated_at > created_at`.

Both are `TIMESTAMPTZ` filled by the database's `now()`, and PostgreSQL's
`now()` is the start of the current transaction, so the create and the edit —
two transactions — cannot collide on the same value.

One property worth knowing before it surprises someone: SQLAlchemy emits no
`UPDATE` when nothing actually changed, so `PATCH` with the value a row already
holds answers 200 and leaves `updated_at` where it was. That is correct, and it
is also why the edit test changes the name to something new rather than
re-sending the old one.

## Consequences

**Every existing list assertion had to become page-aware.** The Phase 10 tests
fetched `/api/items` and expected to see what they had just created. On a
database with more than 20 rows that is no longer true, and the fix is in the
tests, not in a larger default. This is the cost of the decision, paid once.

**stage accumulates rows across cycles.** It is seeded and kept for the life of
the environment, so it is the only place where the second page exists in
practice. The contract suite therefore creates the rows it needs to paginate
rather than assuming enough exist.

**The dashboard is unaffected.** It reads `status/<env>.json` and the GitHub
API (ADR-0026); it has never read `/api/items`.

## Alternatives considered

**Cursor pagination (`?after=<id>`).** Correct under concurrent inserts, where
offset can skip or repeat a row. It also cannot express "page 7 of 12", which
is what the UI shows, and this application has one writer at a time by
construction. Offset is the honest choice at this size; the trade-off is worth
being able to name at interview rather than hiding behind the fashionable
answer.

**PUT instead of PATCH.** A full replacement needs no `exclude_unset` and has no
absent-versus-null question — because every unmentioned field is silently
cleared. That is the trap, not the escape.

**Keeping the list unbounded and adding `limit` as opt-in.** Backward compatible
and pointless: the default is what every client uses.
