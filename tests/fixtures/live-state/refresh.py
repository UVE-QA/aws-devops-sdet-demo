#!/usr/bin/env python3
"""Refresh the FROZEN phase snapshot this gate folds observations against.

    python3 tests/fixtures/live-state/refresh.py

It rewrites `phases.json` from site/data/topology.json, keeping only what the
run-layer state machine reads: each phase's live binding, each node's id,
environment and own binding, the phase's `touches`, and the estate nodes those
touches name.

THE TOUCHES ARE KEPT WHOLE, all five verbs. phaseNodes() takes only `creates`,
and a snapshot that pre-filtered them would be asserting that rule instead of
testing it: with every verb in the file, a resolver that forgot to filter
lights fifteen resource nodes in the teardown and the cases say so.

It deliberately does NOT touch cases/. Those observations and their expected
results are written BY HAND, and regenerating an expectation from the machine
being tested would leave a gate that agrees with whatever the page currently
does - which is the one thing a gate must never be.

Run it when the bindings change on purpose, and read the diff: a case that goes
red afterwards is the gate telling you a rename moved something.
"""
from __future__ import annotations

import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent

NOTE = (
    "A FROZEN snapshot of what the run-layer state machine needs out of "
    "site/data/topology.json: the phase bindings, each node's id, "
    "environment and own binding, each phase's touches, and the estate nodes "
    "those touches name — the machine resolves them through phaseNodes(). Frozen on purpose, exactly like the "
    "inventory in tests/fixtures/results/: this gate is about the state "
    "machine, and if it read the live map then adding a node would redden "
    "it and teach the person who added it that the fixture is stale. "
    "Refresh it deliberately, with tests/fixtures/live-state/refresh.py, "
    "when the bindings themselves change."
)


def keep(node: dict) -> dict:
    return {k: v for k, v in node.items() if k in ("id", "env", "live")}


def main() -> None:
    topology = json.loads((ROOT / "site/data/topology.json").read_text())
    phases = [
        {
            "id": p["id"],
            "live": p["live"],
            "nodes": [keep(n) for n in p["nodes"]],
            "touches": p.get("touches", []),
        }
        for p in topology["cycle"]["phases"]
    ]
    environments = [
        {"id": e["id"], "nodes": [keep(n) for n in e["nodes"]]}
        for e in topology["estate"]["environments"]
    ]

    # A touch that resolves to nothing would quietly shrink the node list this
    # gate folds, and a gate that checks fewer things than it did is the one
    # failure this repository will not see. So it is an error here, where the
    # snapshot is made, rather than a `filter(Boolean)` on the page.
    known = {n["id"] for e in environments for n in e["nodes"]}
    known |= {n["id"] for n in topology["estate"]["permanent"]}
    dangling = sorted(
        t["node"] for p in phases for t in p["touches"] if t["node"] not in known
    )
    if dangling:
        raise SystemExit(f"touches name estate nodes that do not exist: {dangling}")

    out = {
        "_": NOTE,
        "captured_from": "site/data/topology.json",
        "estate": {"environments": environments},
        "phases": phases,
    }
    (HERE / "phases.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print(f"phases.json: {len(phases)} phases, "
          f"{sum(1 for p in phases for n in p['nodes'] if n.get('live'))} nodes with a binding of their own, "
          f"{sum(len(e['nodes']) for e in environments)} estate nodes across "
          f"{len(environments)} environments")


if __name__ == "__main__":
    main()
