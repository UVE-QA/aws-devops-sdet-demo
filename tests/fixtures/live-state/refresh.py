#!/usr/bin/env python3
"""Refresh the FROZEN phase snapshot this gate folds observations against.

    python3 tests/fixtures/live-state/refresh.py

It rewrites `phases.json` from site/data/topology.json, keeping only what the
run-layer state machine reads: each phase's live binding, and each node's id,
environment and own binding.

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
    "site/data/topology.json: the phase bindings, and each node's id, "
    "environment and own binding. Frozen on purpose, exactly like the "
    "inventory in tests/fixtures/results/: this gate is about the state "
    "machine, and if it read the live map then adding a node would redden "
    "it and teach the person who added it that the fixture is stale. "
    "Refresh it deliberately, with tests/fixtures/live-state/refresh.py, "
    "when the bindings themselves change."
)


def main() -> None:
    topology = json.loads((ROOT / "site/data/topology.json").read_text())
    phases = [
        {
            "id": p["id"],
            "live": p["live"],
            "nodes": [
                {k: v for k, v in n.items() if k in ("id", "env", "live")} for n in p["nodes"]
            ],
        }
        for p in topology["phases"]
    ]
    out = {"_": NOTE, "captured_from": "site/data/topology.json", "phases": phases}
    (HERE / "phases.json").write_text(json.dumps(out, indent=2) + "\n")
    print(f"phases.json: {len(phases)} phases, "
          f"{sum(1 for p in phases for n in p['nodes'] if n.get('live'))} nodes with a binding of their own")


if __name__ == "__main__":
    main()
