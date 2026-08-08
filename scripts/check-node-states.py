#!/usr/bin/env python3
"""The gate over scripts/node-states.py.

Joins every case against the stub topology in tests/fixtures/node-states/ and
compares the result with that case's expected.json. Runs in ci.yml; costs
nothing, calls no AWS, and needs no terraform.

The claim it defends: **a resource a cycle created is drawn on the map, is
recorded as deliberately not drawn, or is reported as unknown — never silently
absent.** That is ADR-0039 D1's coverage rule applied to observations instead of
to the repository, and it is the same shape as the spec-coverage guard: a thing
belonging to nowhere fails loudly rather than being reported by nobody.

Two kinds of case, and the difference matters:

    cases/       the timeline is FOLDED FROM A REAL TERRAFORM RUN, reusing the
                 streams under tests/fixtures/timeline/. What is under test is
                 the address terraform actually writes - `[0]` on a resource,
                 `[0]` on a module, a module-qualified address - against the
                 members a static read of infra/ produces
    synthetic/   the timeline is hand-written, and says so in the file. What is
                 under test is arithmetic that is entirely ours, and a real run
                 is WORSE for it: terraform_data finishes in zero seconds, so no
                 real fixture can distinguish "the longest member" from "the
                 first member"

    scripts/check-node-states.py                     # every case
    scripts/check-node-states.py --case apply-module # one

Exit status: 0 if every case matches, 1 otherwise.
"""

from __future__ import annotations

import argparse
import importlib.util
import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FIXTURES = ROOT / "tests" / "fixtures" / "node-states"
CASES = FIXTURES / "cases"
SYNTHETIC = FIXTURES / "synthetic"
STREAMS = ROOT / "tests" / "fixtures" / "timeline" / "cases"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


fold_timeline = load("fold_timeline", HERE / "fold-timeline.py")
node_states = load("node_states", HERE / "node-states.py")


def timeline_for(case: str) -> dict:
    """Fold the timeline fixture of the same name, silently.

    The fold prints a readable log by design — it is half of what that script
    is for — and a gate that emitted six of them would be unreadable.
    """
    stream_dir = STREAMS / case / "streams"
    if not stream_dir.is_dir():
        raise FileNotFoundError(f"{case}: no streams at {stream_dir}")
    operations = fold_timeline.collect_streams(stream_dir)
    if not operations:
        raise FileNotFoundError(f"{case}: no *.jsonl streams in {stream_dir}")
    for op in operations:
        op.read()
    with redirect_stdout(io.StringIO()):
        return fold_timeline.build("stage", operations, {"id": "fixture"})


def summarise(states: dict, expected_nodes: dict) -> dict:
    """Everything the expectation can name, and nothing that changes per run.

    `identifier` and `duration_s` are compared only where the expectation names
    them, because a fixture regenerated from a real run gets a fresh UUID and a
    fresh clock every time — and a gate that had to be rewritten after every
    regeneration would be switched off within a week. The synthetic case names
    both, which is the whole reason it exists.
    """
    nodes = {}
    for node_id, node in states["nodes"].items():
        want = expected_nodes.get(node_id, {})
        summary = {
            "state": node["state"],
            "resources_observed": node["resources_observed"],
            "resources_complete": node["resources_complete"],
            "identifier_present": node["identifier"] is not None,
        }
        for key in ("duration_s", "identifier", "identifier_from"):
            if key in want:
                summary[key] = node[key]
        nodes[node_id] = summary
    return {
        "environment": states["environment"],
        "kind": states["kind"],
        "observed": states["observed"],
        "not_shown": states["not_shown"],
        "read": states["read"],
        "unknown": states["unknown"],
        "nodes": nodes,
        # Which phases lit is stable across regenerations; how long they took is
        # not, so only the synthetic case names durations.
        "phase_ids": sorted(states["phases"]),
        "phases": {
            pid: {"duration_s": v["duration_s"], "nodes": v["nodes"]}
            for pid, v in states["phases"].items()
        },
    }


def compare(case: str, got: dict, expected: dict) -> list[str]:
    findings = []
    for key in ("environment", "kind", "observed", "not_shown", "read", "unknown", "phase_ids", "phases"):
        if key not in expected:
            continue
        if got[key] != expected[key]:
            findings.append(
                f"{case}: {key}\n     expected {json.dumps(expected[key], sort_keys=True)}"
                f"\n     got      {json.dumps(got[key], sort_keys=True)}"
            )
    want_nodes, got_nodes = expected["nodes"], got["nodes"]
    for node_id in sorted(set(want_nodes) | set(got_nodes)):
        if node_id not in got_nodes:
            findings.append(f"{case}: node {node_id} expected and not produced")
        elif node_id not in want_nodes:
            findings.append(f"{case}: node {node_id} produced and not expected")
        elif got_nodes[node_id] != want_nodes[node_id]:
            findings.append(
                f"{case}: node {node_id}"
                f"\n     expected {json.dumps(want_nodes[node_id], sort_keys=True)}"
                f"\n     got      {json.dumps(got_nodes[node_id], sort_keys=True)}"
            )
    return findings


def discover() -> list[tuple[str, Path]]:
    cases = [(p.name, p) for p in sorted(CASES.iterdir()) if p.is_dir()]
    if SYNTHETIC.is_dir():
        cases.append(("synthetic", SYNTHETIC))
    return cases


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--case")
    args = parser.parse_args(argv)

    topology = json.loads((FIXTURES / "topology.json").read_text(encoding="utf-8"))

    cases = discover()
    if args.case:
        cases = [c for c in cases if c[0] == args.case]
        if not cases:
            print(f"no such case: {args.case}", file=sys.stderr)
            return 1
    if not cases:
        # The same refusal check-timeline.py makes. An empty fixture directory
        # passing 0 of 0 is a gate that has quietly stopped existing.
        print("node-states: no cases found. Refusing to pass zero.", file=sys.stderr)
        return 1

    findings: list[str] = []
    for name, path in cases:
        expected = json.loads((path / "expected.json").read_text(encoding="utf-8"))
        if name == "synthetic":
            timeline = json.loads((path / "timeline.json").read_text(encoding="utf-8"))
        else:
            try:
                timeline = timeline_for(name)
            except FileNotFoundError as err:
                findings.append(str(err))
                continue
        states = node_states.join(topology, timeline)
        findings.extend(compare(name, summarise(states, expected["nodes"]), expected))

    if findings:
        print(f"node-states: {len(findings)} finding(s)\n", file=sys.stderr)
        for finding in findings:
            print(f"  - {finding}", file=sys.stderr)
        return 1

    print(f"node-states: clean — {len(cases)} cases, "
          f"{sum(1 for n, _ in cases if n != 'synthetic')} folded from real terraform runs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
