# ADR-0071: The page still describes a cycle that had three jobs and one kind

## Status
Proposed (Phase 36, 2026-09-06). Two consequences of **ADR-0068** that it did not
anticipate and this session found by watching a real cycle. Neither is fixed
here; both are recorded with the evidence.

## Context

Until ADR-0068 a self-service cycle was one shape: three jobs — `launch`,
`destroy`, `release-lock` — of which usually one had ever run, and one set of
suites. The page's vocabulary and layout were built for that.

ADR-0068 made it six jobs across three workflow files, running a *subset* of the
suites. The page was not revisited, and two of its sentences are now wrong in
ways a reader notices before anybody else does — both were reported by the owner
looking at the live page, not by a gate.

### Finding 1 — "the step in flight" leads with steps that landed half an hour ago

The Current cycle panel iterates **every** job in the run and renders each with
its step list. With three jobs and one of them run, the first thing under the
heading was the thing happening. With six, four of them finished, the live job is
last — below four collapsed step lists — and the panel opens with:

```text
CURRENT CYCLE — the step in flight, not the whole log
self-service launch by the owner #12       RUNNING · 45M 23S
launch — success · 14m 22s
  ✓ Post Configure AWS credentials   ✓ Complete job
  all 27 steps · 27 done
```

`destroy-prod / destroy` was running at that moment and appears nowhere above the
fold. The owner's words: *the caption disappeared but what is happening is not
clear.* A panel whose heading promises the step in flight, and which leads with a
job that succeeded thirty minutes earlier, is telling the reader to look at the
wrong thing.

**It is worse right after the hold.** The countdown tile removes itself the moment
its deadline passes — correctly, it has nothing left to say — and the teardown it
was counting towards starts at exactly that moment. So the page goes from its
loudest element to silence precisely when the most interesting thing begins.

### Finding 2 — `not reported` is the vocabulary of absence, used for a decision

A public cycle runs `smoke` and the seed assertion, and deliberately not the API
contract or the destructive regression suite. `self-service.yml` says why:

> SMOKE ONLY … the destructive regression suite belongs on stage and is
> deliberately left out here: a public launch is a demonstration under a deadline,
> and the visitor gets a working environment rather than one a test suite has been
> writing to.

The page draws those two as:

```text
API contract   not reported · 52 tests collected · the last run here did not report this suite
regression     not reported · 12 tests collected · the last run here did not report this suite
```

*The last run here did not report this suite* is what the page says when a report
went missing. Here nothing went missing: the suite was never going to run. A
reader cannot tell a deliberate omission from a lost report, and the difference
is the whole point — one is a design decision and the other is a defect.

**The project already has the right vocabulary and it does not reach here.**
`not_in_cycle` carries a mandatory reason, and `generate-topology.py` fails the
build for a suite with neither a run node nor that reason (ADR-0054 D8). But it
is a property of a SUITE, not of a KIND of cycle: `tests/unit` declares it
because nothing can ever run it against an environment. `regression` is not that
— a stage cycle runs it, a public cycle does not.

## Decision

### D1 — the panel leads with what is in flight

The in-flight job comes first, and finished jobs follow it or fold away. What the
heading promises is what the panel opens with. The ordering rule is the panel's,
not the API's, and the API's order is the order jobs were declared.

### D2 — a suite says which cycles run it, not just whether any do

`not_in_cycle` grows from a boolean-with-a-reason into an answer per kind of
cycle, so a suite can say *this one does not run me, and here is why* without
that reading as a missing report. The wording for a deliberate omission must not
be reachable by a lost one, and the reverse.

### D3 — the hold hands over rather than vanishing

When the countdown reaches zero the tile is removed, which is right, and nothing
replaces it, which is not. The teardown starting is the event the countdown
existed to announce, and the page should say it has started.

## Consequences

- D2 touches `assets/topology-groups.json`, `scripts/generate-topology.py` and its
  refusal, so the schema and the gate move together. It is the larger half.
- **No gate would have caught either.** Every page fixture is built from a cycle
  of the old shape - one kind, three jobs - so the fixtures cannot express a run
  with six jobs and a subset of suites. Whatever is done for D1 and D2 needs a
  fixture of the NEW shape first, or it will be checked against the world that
  made the bug.
- Both were found by a person looking at the live page during a run. That is the
  fifth and sixth such finding on this dashboard, against zero found by the gates
  in the same period, and the pattern is now worth stating plainly: these gates
  check what the page SAYS about data it is given, and nobody checks what the
  page is like to read while something is happening.
