# ADR-0057: One list of gates, two readers

## Status
Accepted (Phase 23, 2026-08-11). Closes the item Phase 22 handed forward in
`docs/next-phases.md` and in `scripts/session-close.sh`'s own comment. Adjacent
to **ADR-0033**, which turned session entry and exit into commands: this is
about what the exit command is allowed to not know.

## Context

`scripts/session-close.sh` ran three cheap gates. `.github/workflows/ci.yml` ran
twelve. Nothing kept the two in step, so `session-close: clean` and a red `main`
were compatible states — and that pair of states occurred twice:

```text
20i  docs/decisions gained ADR-0051; topology.json was generated before it and
     never again. Caught on the devbox before it reached main. Fixed by 1d8980b.
21   the same thing with two ADRs, 54 against 56. It reached main: run
     31343885958 was red while session-close printed clean.
```

Both are the same mechanism, and it is specific rather than careless.
`site/data/topology.json` COUNTS the files in `docs/decisions/`, so a
documents-only session — which is exactly what a decisions phase is — moves a
generated number without going anywhere near the generator.

Phase 22 added the two generated-artifact checks to `session-close.sh` and wrote
in the same commit that this did not close the problem: the list was still two
lists, and the next gate added to one of them would open the gap again.

## Decision

### D1 — The list is data, in one file

`assets/gates.json` carries every gate this repository has, each with one
question answered: can a plain checkout run it — python3 and node, no docker, no
browser, no scanner, no AWS credentials. Everything that answers no carries the
reason it cannot.

### D2 — Both readers call the same target

`make gates` runs the runnable ones. `scripts/session-close.sh` calls it at the
end of a session; `ci.yml` calls it as one step in `terraform-checks` in place of
twelve. There is no third copy, and no reader holds a list of its own.

### D3 — The runner names what it did not run

Rows, not omissions. A gate absent from a table looks exactly like a gate that
passed — Phase 22 found that with a skipped browser gate — so `make gates`
prints every excluded gate with its reason under a heading that says so.

### D4 — One list can shrink in silence, so the list is discovered against

This is what two lists were accidentally protecting: deleting a gate from one of
them left the other one running it. Deleting a line from a single list weakens
both readers at once.

So `make gates-check` derives what ought to be in the list, out of the
repository rather than out of a second list:

```text
a Makefile target whose name ends in -check
a Makefile target whose recipe runs a scripts/check-* program
any target ci.yml invokes as `make <target>`, on a line that is not a comment
```

minus the list's own two targets, which the file names rather than the script
hardcoding them. It refuses when something discovered is not in the list, when
an entry names a target the Makefile does not define, when an exclusion gives no
reason, when a target is listed twice, when the list is empty, and when
`ci.yml` itself is missing — because half a discovery is not a discovery.

The second rule is not decoration: `action-pins` is a gate whose name does not
say so, and the first and third rules would both have missed it.

### D5 — The refusals run before the gates, inside `make gates`

A broken list must refuse, not quietly run a shorter suite. Running twelve of
thirteen gates and printing green is the failure this whole ADR is about, one
level down.

### D6 — The per-gate rationale stays in the Makefile

Collapsing twelve CI steps into one would have deleted twelve explanations. They
were already beside their targets in the Makefile; the four sentences that were
only in `ci.yml` moved there, and the step's own comment now carries only what
belongs to the step — what the runner provides, and what is deliberately not in
it.

### D7 — The phase runner delegates, and the browser gates are a flag

`scripts/verify-schema3.sh` held a third array of eight cheap gates, one day old
and already four short of `ci.yml`. It calls `make gates` for those now, and
derives the two browser gates from `browser: true` in the list rather than naming
them, refusing if the list marks none — because a browser gate missing from that
table is exactly how Phase 22's stale-figures defect reached another host.

## Consequences

- A gate added to `ci.yml` and not to the list reddens `gates-check`. A gate
  added to the Makefile with a `-check` name, or with a `scripts/check-*`
  recipe, does the same. Adding one is now a two-line edit in one file.
- A session's exit check got twelve times stronger without a session having to
  remember anything, which is the property `make session-close` exists for.
- CI's `terraform-checks` job shows one check named `Every cheap gate…` instead
  of twelve named steps. That is a real loss: a red build now says which gate
  failed in the log rather than in the job list. Accepted deliberately — twelve
  readable step names were what made the two lists look maintainable, and the
  runner prints a table naming the failing gate as its first line of output.
- The exit status a caller sees through `make` is 2, not 1: `make` translates a
  failed recipe. Both readers test for non-zero, and the break test records the
  script's own status separately rather than quoting make's.
- `gates-check` cannot see a gate that is neither named `*-check`, nor runs a
  `scripts/check-*` program, nor is invoked by `ci.yml`. Such a gate can still be
  listed by hand and will run; it simply is not discovered. Naming the next gate
  in one of those three shapes is cheaper than a fourth rule.
- The list carries twelve non-gate targets — `local-up`, `migrate`, `test-smoke`
  and the rest — because `ci.yml` invokes them and the discovery cannot tell a
  gate from a step. Each says what it needs and none is runnable in a checkout,
  so the runner's second table doubles as an honest statement of what a plain
  clone cannot verify.
- A phase runner that lists gates is now a thing to look for. `verify-schema3.sh`
  was written one day before this phase and was already the most out-of-date of
  the three lists; nothing discovers a list held in a script, and the discovery
  rules deliberately do not try.
- No AWS cost, no cycle, nothing applied.
