# 2026-08-10 — Phase 22: the model in the data, and a red main nobody saw

The cursor's next allowed step after 21: **the model in the data**, with the page
left alone. `topology.json` goes to schema 3 — estate, cycle, assertions — the
generator is rewritten around it, and every consumer follows. No cycle, no AWS
call, nothing applied. **Cost: $0.** **ADR-0056.**

Break-test output for the six generator refusals in
`docs/sessions/2026-08-10-phase-22-schema3-break-test.log`; the session-close
break test in `docs/sessions/2026-08-10-phase-22-session-close-break-test.log`.

Four findings and three process failures, in that order, because the process
failures are the reusable part.

## 1. Main was red before this phase started, and only a control found it

The session ran the checks BEFORE touching anything. `counts.adrs` in the
committed `site/data/topology.json` said **54**; `docs/decisions/` held **56**.

```text
21          added ADR-0054 and ADR-0055 and never re-ran the generator
082fbaf     the last commit that wrote topology.json, in 20l
run 31343885958   RED on main, while `make session-close` printed `clean`
```

**Second occurrence of the same shape.** The first is `1d8980b`, in 20i: one ADR
added, the topology generated before it and never again, green in the chat's
sandbox and red on the devbox.

The recurrence is the interesting half. `session-close.sh` ran
`check-docs-references.py` and nothing else — and `topology.json` **counts the
files in `docs/decisions/`**, so a documents-only session, a session that
deliberately touches no code, moves a generated number without going anywhere
near the generator. The exit check could not see the one artifact a decisions
phase is guaranteed to invalidate.

```text
4d4662a   the count corrected: 54 -> 56
7fc790c   session-close checks the generated artifacts, not only the prose
519051c   its break test, broken both ways: a stale topology.json AND a
          hand-edited site/index.html, each caught, each restored
```

**NOT CLOSED.** `ci.yml` runs five more cheap gates that `session-close.sh` does
not — `timeline-check`, `node-states-check`, `results-check`, `live-state-check`,
`page-tense-check`. Two lists that can disagree is the defect one layer up from
this one, and it is written into Phase 23 rather than patched here.

## 2. The verb was not in ADR-0054, and counting found it

ADR-0054 D2 makes the binding a reference and says the four phases touching a
database "each say so separately". Written as a bare list of ids it type-checks
and cannot be drawn. Measured:

```text
stage-gate   4 own suite nodes + 3 referenced estate nodes = 7  >= WIDE_AT (6)
             the phase goes two columns wide, layout.columns 10 -> 11
```

A reflow, in the phase whose plan says the page is not touched. So a reference
carries a **verb** — `creates, pushes, provisions, asserts, destroys`, a closed
vocabulary, a sixth is a red build — and a phase draws only what it `creates`.
**ADR-0056.**

Geometry then measured rather than assumed, by lifting `phaseNodes()` out of the
built page and comparing its answer with the last schema-2 file:

```text
1, 7, 1, 4, 1, 8, 2, 2     wide = [stage-apply, prod-apply]     columns = 10
identical to schema 2, node for node, in the same order
```

The words for this were already in ADR-0054 and nothing would have forced them.
What forced them was a column count that changed.

## 3. The obvious refusal could not have failed

ADR-0054 asked for the missing check: a suite that no node draws is a red build.
Written as *"every suite gets a node"* it is **vacuous** — the nodes are
GENERATED from the suites, so the check would have been the generator agreeing
with itself, in the family of `docker compose config --images`.

The one written instead has a reachable false answer: **every suite is either
run by the cycle or declares `not_in_cycle`**. `tests/unit` is the second and now
says so, in its own words, in the data:

```text
in-process and importing the application, so there is nothing for a cycle to run
it against: it runs in ci.yml and locally. Declared rather than inferred - a
suite with neither a run node nor this reason is a red build (ADR-0054 D8).
```

Six refusals broken on purpose, each with distinct output: the two suite ones,
the re-pointed citation (`touches prod.rdz`), the unknown verb (`'pokes'`), the
re-pointed coverage refusal, and a schema-2 leftover phase still holding a
resource group.

## 4. Eight green gates hid two broken consumers

Schema 3 landed in `068b06d`. Every cheap gate was green. Two of the four
consumers were **completely broken**:

```text
node-states.py     index_members() returned ZERO addresses from the real file.
                   Every resource of a live cycle would have been reported
                   UNKNOWN - the one channel that is supposed to be rare
index.template     read DATA.phases, which no longer exists. The map would have
                   thrown on load
```

Green because every one of those gates reads a **frozen schema-2 fixture**. The
fixture and the code agreed with each other, and neither had seen the file the
code is handed. An instrument aimed at an object that had stopped existing.

The repair is `scripts/verify-schema3.sh`, and the row that matters in it is not
a gate:

```text
probe   ok   index_members(stage) = 29 addresses      (before: 0)
```

It loads `node-states.py` by path, hands it `site/data/topology.json` itself and
counts what comes back. Every status in that runner is captured into its own
variable on its own line — `$?` after a pipeline is the pipeline's last command,
and a gate that failed while `grep` matched its own error text reads as a pass.

## 5. The gate this session could not run caught the only regression

`page-freshness-check` was **red 3 of 3 on the devbox** while the sandbox was
green on twelve rows. An open tab held the pre-cycle figures in all four
compared regions while a fresh load showed the post-cycle ones — ADR-0053's
defect, reintroduced by this phase.

```text
map    open tab  Apply — stage 7m 0s        fresh  10m 5s
sub    open tab  dated 2026-08-08           fresh  dated 2026-08-09
cost   open tab  HIDDEN                     fresh  stage $0.0526 .. $0.0581
```

**One identifier in the wrong scope.** 20m's history-badge fix needed a scoring
function; it was written into the MAP's script, which is wrapped in an IIFE on
purpose — *"nothing here is meant to be reachable from there"* — and its only
caller, `renderHistory()`, is in the dashboard's script.

```text
renderHistory()   threw ReferenceError on every tick
renderAll()       died before announceCycle() and scheduleRefresh()
the map           never got another observation, so since 20l it never re-read
                  the run layer: figures, dating sentence and cost box frozen
the tab           never scheduled another bucket tick, and Refresh re-threw
```

Three symptoms, one stack frame. Every other gate stayed green because a cold
load renders from the map's own bootstrap chain, which never goes through
`renderAll()`.

**A chat session without a browser cannot see this class of defect at all.** The
lifted-block gates say what a function ANSWERS; the fixture gates say what a fold
produces; neither can see that a call throws. Two things follow, both done:

- the fix is `historyTally()` beside its caller, in a lifted block of its own,
  and `check-page-tense.mjs` lifts BOTH blocks into one context;
- the coupling check learned that the page has two scopes. It now requires each
  lifted function to be called from the SAME `<script>` as its block. Moving the
  marked block back inside the wrapper was green before (14 cases, 38 calls) and
  REFUSES now. A text gate cannot know about scopes; it can know that a
  deliberately wrapped script is not a place to put a function somebody else
  calls.
- `verify-schema3.sh` prints the browser gates as rows **whatever happens**. With
  Playwright present they run; without it they read `SKIP`, name the command that
  installs it, and the closing line says the run is INCOMPLETE. A gate absent
  from a table looks exactly like a gate that passed, which is precisely how this
  reached another host on twelve green rows.

The root cause was reproduced under jsdom before it was fixed — same two fixture
sets, same four regions, same control line — and the fix verified the same way,
then confirmed with a real browser on the devbox: **14/14, both browser gates
included.**

## Three process failures, all self-inflicted, all in the primer

### (a) A break test that could not have distinguished six gates from one

The first run of the six-refusal break test was **worthless and looked perfect**.
Each probe ended with `git checkout` — and the editorial file was not yet
committed, so the first restore reverted it. All six probes then hit the same
refusal, `no estate.environments`, and produced six red readings that are
indistinguishable from six working gates.

### (b) The same `git checkout -- .` destroyed the generator

Every uncommitted edit to `scripts/generate-topology.py` went with it, and the
whole assembly had to be rewritten from a patch script.

### (c) An anchor that survives its own replacement

In the follow-up session, `scripts/migrate-schema3.py` — the patch script that
exists BECAUSE of 19g's "computed every replacement from the original text and
printed success twice" — had three anchors contained in their own replacements.
Running it twice would have inserted those blocks a second time, and its
"already applied" test could never fire for them. The invariant is now checked
before anything is read for matches: an insertion anchors on text the insertion
BREAKS, the lines either side of it.

`docs/session-primer.md` says **COMMIT BEFORE BREAKING THINGS ON PURPOSE**, and
(a) and (b) happened in the session that quotes it. (c) is the same species one
level up: a tool written against a documented failure, reproducing a variant of
it. The three are recorded here at length because they cost more than any of the
findings did.

## What changed

```text
assets/topology-groups.json          the estate its own section; phases hold
                                     references, each with a verb
scripts/generate-topology.py         schema 2 -> 3, the assembly rewritten;
                                     coverage refusals re-pointed to estate
                                     nodes; the suite refusal added
scripts/migrate-schema3.py           the patch script for the four consumers.
                                     One read, one write per file; an anchor
                                     matching other than exactly once changes
                                     NOTHING; exit 3 = already applied
scripts/verify-schema3.sh            the runner: every gate, the browser gates
                                     as SKIP-able rows, and the real-file probe
scripts/node-states.py               members from estate.environments[].nodes,
                                     verb nodes from cycle.phases[].nodes,
                                     phase_of() resolving `creates` only
scripts/fold-results.py              the suite ids, one contour over
assets/index.template.html           phaseNodes(p), useEstate(), every read
                                     site routed through them; the run-history
                                     badge; site/index.html rebuilt
scripts/check-live-state.mjs         the snapshot carries the estate; all five
                                     verbs kept so the filter is under gate
scripts/check-page-tense.mjs         two blocks, one context, and the
                                     same-script coupling check
scripts/session-close.sh             the generated artifacts, not only the prose
tests/fixtures/…                     node-states and results stubs to schema 3;
                                     live-state snapshot regenerated; one new
                                     page-tense case
docs/decisions/0056-a-reference-carries-a-verb.md
```

## The closing condition, and the reading taken

Phase 22 closes on: `make site-data-check` green on a schema-3 topology in which
no phase contains a resource node, every reference resolves, **all five suites
are drawn**, the new refusal broken on purpose once with its output kept, and the
badge fix carrying a case that fails without it.

Checked one at a time against the committed file:

```text
no phase holds a resource node   cycle nodes: 3 service, 1 task, 6 suite,
                                 1 gate - none carries `members`
every reference resolves         39 touches, 0 unresolved, 5 verbs, and the
                                 build refuses an unresolvable one by name
all five suites                  assertions.suites = 5, tests/unit included
                                 with its `not_in_cycle` reason
the refusal, broken              six of them, output kept in the log
the badge case                   red without the fix, and only that case
```

**`drawn` is read as `present in the topology`.** All five suites are in
`assertions.suites`; **nothing on the PAGE renders the assertions contour**,
because Phase 22 forbids touching the composition and rendering it is a
composition decision. Recorded rather than quietly satisfied: the page's
rendering of the assertions contour is written into Phase 23 in
`docs/next-phases.md`.

## Validation

```bash
  scripts/verify-schema3.sh
  make site-data-check site-page-check docs-check
  make node-states-check results-check live-state-check page-tense-check
  make page-freshness-check contrast-check      # devbox only, needs chromium
```

```text
devbox    14/14 green, page-freshness-check and contrast-check included
sandbox   12/12 green, 2 SKIP, probe = 29 addresses, run says INCOMPLETE
```

## Cost

**$0.** No AWS call, no cycle, nothing applied, nothing launched.

## Next

**Phase 23 — the composition, re-measured, and the gate for a cycle in flight**,
as planned, plus two items this phase adds to it: render the assertions contour,
and the two-list problem between `session-close.sh` and `ci.yml`.
