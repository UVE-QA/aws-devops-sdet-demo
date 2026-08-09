# 2026-08-09 — Phase 20e.1: the floor is met before the layout, and three blockers close

**ADR-0048.** Break tests in
`docs/sessions/2026-08-09-phase-20e-1-contrast-gate-break-tests.log`.
Cost: nothing. No cycle, no AWS call, nothing applied. `site/index.html` and
`site/data/topology.json` change, so the published dashboard changes with the
next push — a static sync, no infrastructure.

The session took the cursor's next allowed step and deliberately took only part
of it: the three open items that block layout, and the gate ADR-0047's own
Consequences asked for. The composition itself is not started.

## Three decisions, made before a line of layout

The order was chosen for one reason: 20e.0's finding was that aiming an
instrument before establishing the requirement costs a phase, and layout is an
instrument.

```text
the Launch button   the Environments panel's FOOTER. Not the identity bar -
                    a control that spends money does not sit in a row of
                    links - and not the current-cycle panel, whose content
                    varies, because a control that moves is worse than one in
                    a boring place. It acts on what that panel observes, and
                    its refusals ARE environment state.
the legend          a cut in the map's header, closed by default. D6 put a
                    word on every node, so the legend stopped being a decoder.
                    And explicitly: the sketch's "State encoding" strip does
                    NOT go on the page - it exists to show a reader the new
                    encoding, which is evidence, not an element.
the node's figures  one state line under the head, <word> · <figure>, word
                    first. No badge in the head, no second row - and where
                    there is no figure, no separator either, because
                    "passed · " with nothing after the dot is the empty
                    result that looks clean.
```

## The gate, and why it needed a browser

`make contrast-check`, `scripts/check-contrast.mjs`, states declared in
`assets/contrast-contract.json`. It is the first gate here that renders
anything: it lifts the `<style>` blocks out of the BUILT page — the same move
`check-live-state.mjs` makes on the same file — and measures them in chromium,
because the engine is what resolves `color-mix()`.

That is not a preference. The one contrast measurement this project has already
taken was WRONG and looked like a finding, in a colour parser: `color-mix()`
resolves to `color(srgb 0.44 0.62 0.90)`, whose components are already 0..1, and
dividing them by 255 returned 20.92:1 for six different colours. So the control
runs before anything else, on every invocation — black on white must read 21.00
through the hex notation AND through the srgb-float one — and a control that is
off is a REFUSAL with no verdict, not a failing check with a table under it.

**It reproduced ADR-0047's table to the hundredth on five of six states**, in
both themes, written from scratch and sharing no code with the discovery's
throwaway script, which was never committed. That is the strongest evidence
available that both instruments are right about the model.

The sixth is a finding. `absent` reads 1.15 / 1.12 here against 1.34 / 1.35
there, and it is the only state carrying `opacity: 0.45`. The older figure is
not a different model, it is **unreachable**: `#d8dbe2` against pure white — the
lightest thing there is — is 1.27, so no background produces 1.34. ADR-0048 D4
supersedes that row. Nothing follows from it; `absent` is exempt from the floor
on purpose and was under it on both readings.

## The palette moved first, and on purpose

The floor is met on the CURRENT page, before any composition:

```text
                before          after      floor 3.0:1
  working    2.67 / 3.65    3.22 / 4.76
  done       2.41 / 3.28    3.37 / 5.35
  suite      1.98 / 2.73    3.38 / 5.50
  live       4.63 / 7.62    unchanged
  failed-now 3.17 / 3.29    unchanged - nothing measured a need to move it
  absent     1.15 / 1.12    unchanged - exempt, the word carries it
```

Percentages measured rather than chosen: the smallest 5% step clearing the floor
with a margin in both themes. Each boundary is now a token in `:root` —
`.node.done` and `.phase.done` used to be the same colour by hand rather than by
construction, which is one definition written in two places, the shape that
handed the image scan `postgres:16`.

Landing the fix before the gate is the rule this project already paid for once:
when the image scan reached `main`, four Dependabot PRs went red over findings
none of them introduced.

## The break test

Seven breaks, green control either side, exit statuses read from `$?` directly
rather than through a pipe, and the sha256 of every input printed on every run.

```text
1  a state put back under the floor        RED, naming suite
2  --ok lightened, no state colour edited  RED, done falls 3.37 -> 1.68
3  the discovery's parser defect replanted REFUSAL on the control, 1.01 not 21.00
4  an empty contract                       REFUSAL - zero states is not a pass
5  no contract at all                      REFUSAL
6  a probe that is not a colour            REFUSAL, never a skip
7  the built page missing                  REFUSAL
```

Break 3 is the one that matters and it is not about contrast: it proves the
instrument catches the exact defect that produced a wrong reading here before.
Break 2 is the one the gate exists for — nobody edits a state colour to be
fainter; a shared token moves and every mix toward `--line` follows it quietly.

An eighth refusal fired for real, unplanned, during development: playwright
resolved from a CommonJS package with no synthesised named export, and the
script refused naming both paths it had looked in rather than falling back to
parsing the CSS itself. A fallback there would have been a control that
reproduces the defect.

## What was NOT done, and why

**The map's computed column span total (ADR-0047 D5) is deferred to the layout
commit.** It can be computed today — the generator has the node counts — but the
grid that would consume it does not exist yet, and a number nothing reads has
never been exercised. Landing it now would be a value that looks finished; this
project's recurring failure is not "it broke" but "it looked finished".

The composition itself, and the phone, are untouched.

## Housekeeping

Seven patches were sitting in the transfer buffer's `outbox/` at the start of
this session — `phase-20e-1..3` and `phase-20f-1..4` — and all twelve of their
commits are already in `origin/main`. A chat cannot delete from the buffer;
reported rather than left silent, which is now the second session in a row to
report it.

The copy of `docs/session-primer.md` on the MacBook was verified byte-identical
to the repository's, by hash rather than by assertion.
