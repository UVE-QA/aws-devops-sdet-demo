# ADR-0054: A process and a state are two contours, and what binds them is a reference

## Status
Accepted (Phase 21, 2026-08-10). No code; the model only. Implementation is
Phase 22 (the model and the generator) and Phase 23 (the composition and the
gates), per **ADR-0055**.

Supersedes **ADR-0039 D2b**'s first half — the clause forbidding a tests panel —
and relocates its second. Supersedes **ADR-0047 D1** (the five-block
composition, and `permanent` under a cut) and **ADR-0052 D2** and **D3**.
Extends **ADR-0039 D1** and **D4**, **ADR-0043 D2**, **ADR-0047 D3/D4/D5**,
**ADR-0049 D2**, **ADR-0045 D5**. Reuses **ADR-0049 D6**'s citation mechanism
unchanged. **ADR-0042** is untouched and is the precedent this ADR generalises.

## Context

The dashboard already separates a process from a state, and the map underneath
contradicts it:

```text
p-env   "Environments — observed in AWS, not inferred from a green run"
p-run   "Current cycle — the step in flight, not the whole log"
map     "What a cycle does, in the order it does it"
          └─ stage.vpc, stage.rds, stage.alb, stage.ecs, prod.rds …
```

Every environment resource is drawn twice: once as state in the panel, once as a
child of the phase that creates it. The two accounts disagree often enough that
somebody had to write the arbiter down — `tests/fixtures/page-tense/cases/`
holds a case named `an-environment-is-what-the-panel-above-the-map-says-it-is`.

**The nesting is the wrong encoding of the relationship.** `stage-apply created
stage.rds` is a reference; the map stores it as containment, and containment
gives a noun exactly one verb forever. In fact four verbs touch `stage.rds`:
apply creates it, provision migrates into it, the quality gate asserts against
it, destroy deletes it. The map can draw the first.

Two of Phase 20m's three findings follow directly. The node renderer consults the
run layer before `nodeTense` because a node **is** a step, and for a step the run
layer looks authoritative. And `prod.rds`, drawn under `prod-apply`, is
unreachable from the destroy phase — so it stood at full colour with the previous
cycle's figures for twelve measured minutes while prod was being deleted.

What makes this cheap is that most of the model already exists, unnamed:

```text
assets/topology-groups.json   groups[].kind = permanent | node | hidden
observer on every node        terraform | report | actions
perm.ecr / build.ecr          the registry-noun and the push-verb, already apart
destroy.stage / destroy.prod  a verb referencing a whole level by path
ADR-0049 D6, request_path     hops[].cites names a node BY ID, and the build
                              refuses a citation the map cannot honour
envObservation / envPanel     stage and prod, present tense, from
                              status/<env>.json, which says nothing about a run
```

## Decision

### D1 — Three contours, each named by what answers for it

```text
ESTATE       the nouns. Permanent levels, stage, prod.
             Present tense. Answered by observation in AWS —
             scripts/observe-environment.sh → status/<env>.json.

CYCLE        the verbs. build, apply, provision, gate, approve, apply, destroy.
             Past, or in flight. Answered by the run layer and the folded
             timeline.

ASSERTIONS   what the repository claims and checks. The five suites.
             Tenseless. Answered by the repository — scripts/collect-suites.py.
```

Nothing here is invented. `groups[].kind` and `observer` are this distinction
already, carried in the data and read by the renderer (ADR-0051 D3) without ever
being given a name. This ADR names it and makes the page obey it.

### D2 — The binding is a reference, and it is the mechanism already in the build

A cycle step names, by id, the estate nodes it touches. An estate node names the
step that last touched it. Neither contains the other.

This is `request_path`'s `cites` (ADR-0049 D6) applied a second time: the
generator builds the set of ids that exist and **refuses** a reference naming
anything outside it. Both of that refusal's paths were exercised when it shipped.
What moves is the construction of the known set; the mechanism does not move at
all.

The property worth stating, because it is the one nesting cannot have:

```text
A NOUN MAY BE TOUCHED BY ANY NUMBER OF VERBS, AND EACH SAYS SO SEPARATELY.
```

### D3 — Tense is a property of the contour, not of the node

Estate is now. Cycle is then, or running. Assertions have no tense.

Today one map is required to be two tenses at once; `nodeTense` was written in
20i to arbitrate, and 20m proved that while a phase runs nothing calls it. Under
D1 the question does not arise for an estate node: it is drawn from an
observation that has no tense problem, and ADR-0051 D2 already refuses to
re-derive that observation from the run layer.

### D4 — ADR-0039 D2b, both halves

D2b reads: *"each suite that runs appears as its own node in the sequence —
beside the services, not in a panel next to them. A separate tests panel would be
a second place telling the same story."* And: *"A node is a suite × ENVIRONMENT,
not a suite."*

**The first half is overturned.** Its argument — one story, two places — is the
argument for this ADR, and D2b applied it to the wrong object. A suite carries
**two** facts, not one: what it contains, which is a property of the repository,
and how it ran, which is a property of a run. ADR-0042 D5 already split exactly
those two into `site/data/suites.json` and `results/<env>/latest.json`. So the
duplication D2b feared is what the page does today; separating the contours ends
it rather than creating it.

**The second half is not overturned. It was always about the run.** A suite is
one node in ASSERTIONS. A *run* of a suite is suite × environment and belongs to
CYCLE. Both statements were true under D2b and it had only one place to put them.

### D5 — The estate contour absorbs the environments panel, and permanent leaves the cut

`envPanel` is already the estate contour for stage and prod. It is joined to the
map's resource nodes by nothing, which is why the map can contradict it. The
resource nodes move into the panel's contour and stop being a second account.

Permanent levels are nouns and belong with the other nouns. ADR-0047 D1 put them
under a cut on the grounds that the first screen is the cycle; under D1 the first
screen carries both contours, and that placement goes with the composition it
belonged to.

### D6 — A figure is drawn where it is owned, not where it was computed

Cost is a lifetime (ADR-0045) and a lifetime is a property of the estate. The
teardown computes it (ADR-0046). So the figure belongs to the estate node, the
computing event belongs to the cycle step, and ADR-0051's "which cycle is this
figure about" caption hangs on the estate contour as a whole.

That caption is 20m's third finding. It is attached today to `destroyed` and to
nothing else, so during `unknown` — the state an environment is in whenever a run
touches it — the figures are presented unqualified. Under D6 there is exactly one
place for it to live and no state it can be forgotten in.

### D7 — What this does not fix, said before anyone assumes it does

20m's **first** finding is a counting bug inside the cycle contour: the run
history badge takes a numerator of completed runs and a denominator of all of
them, so a run in flight is scored a success before it finishes. It is unaffected
by this ADR, it needs no fixture holding a cycle mid-flight, and it is fixed on
its own in Phase 22.

And making two defects structurally impossible is not evidence that they are
gone. Phase 23 still owes the thing the cursor named after 20m: a fixture holding
a cycle **in mid-flight** with an otherwise-green history, a gate that reads it,
and a break test on that gate. Every gate here has one.

### D8 — `topology.json` goes to schema 3, and the split happens in the editorial file

`assets/topology-groups.json` is the single place the nesting lives, and it says
of itself that it carries the two things `infra/` cannot: which display group a
resource block belongs to, and how groups are arranged into phases. The second is
what changes. A phase stops holding nodes and starts holding references; the
estate becomes a section of its own; the generator's coverage refusals re-point
from group→phase-level to group→estate node.

One refusal is added, for a hole this found: `counts.suites` reports 5, the map
draws 4, and `tests/unit` is inventoried, counted and invisible. ADR-0039 D2b
claims *"a spec directory belonging to no display node is a red build"*; that is
enforced between suites and collectors, and never between suites and the map. The
assertions contour draws all five, and the missing refusal is written.

## Consequences

- Two of 20m's three findings become unrepresentable rather than fixed. The
  third is a counting bug and is fixed separately (D7).
- **Retired, not restated:** every measured layout figure in ADR-0050 and
  ADR-0052 — the comb band, the air, the 2039/2205/2346/2219 comparison written
  into `scripts/generate-topology.py`. They are measurements of an object that
  stops existing. Phase 23 measures the new one; it does not translate the old
  numbers.
- **Rewritten:** `scripts/generate-topology.py`'s assembly, which is most of the
  work; `scripts/check-live-state.mjs` and its fixtures, whose cases are
  hand-written and whose `via: "own"` / `via: "phase"` expectations have to be
  re-derived by hand; `scripts/node-states.py`'s four indexers and their fixture
  stub; one comprehension and one frozen stub under `scripts/check-results.py`.
- **Re-run only:** `make site-page-check`, `make timeline-check` (it never reads
  the topology), `make suite-inventory-check`, `make page-tense-check` provided
  the four lifted functions keep their signatures, and `make contrast-check`,
  which reads its ancestry from `assets/contrast-contract.json` as data. If a
  seventh node state appears the contrast contract refuses it by design, out
  loud, which is the behaviour we want and a task to remember.
- `layout.columns` recomputes. The current 10 is 8 phases plus 2 wide ones, and
  the wide ones are wide because of resource nodes that leave.
- No AWS cost, no cycle, nothing applied. The published page changes, so the next
  push republishes it.
- ADR-0046 D5 keeps this cheap in one place nobody would predict: the wired
  teardown does not pass `--nodes`, so per-phase cost attribution is not computed
  in production today at all.
- The honest risk: the composition was fought for across three sessions in 20e,
  20g and 20j, and this re-opens it deliberately. That is the price of the model
  being wrong underneath a layout that is right.
