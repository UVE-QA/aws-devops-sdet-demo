#!/usr/bin/env python3
"""The gate over scripts/fold-results.py.

Folds every case under tests/fixtures/results/cases/ and compares the outcome
against that case's expected.json. Runs in ci.yml; costs nothing and calls no
AWS.

The claim it defends: **a run's report decides what a suite node says, and
everything the report does not cover is named rather than coloured.** A fold that
marked everything incomplete would satisfy that sentence and be useless, so the
green, red and partial cases are checked just as exactly - counts included.

WHAT IS COMPARED. Statuses, per-status counts, the unobserved list and the
unknown map. Not durations: they differ on every generation, and a gate that has
to be regenerated after every run is a gate that gets turned off.

WHY THE INVENTORY IS FROZEN HERE. tests/fixtures/results/inventory.json is a
snapshot, not a link to site/data/suites.json. This gate is about the FOLD; if it
read the live inventory, adding one test to tests/api would redden it, and the
person who added the test would learn that the fold is fine and the fixture is
stale - which is how a gate teaches people to ignore it.

    scripts/check-results.py                  # every case
    scripts/check-results.py --case db-green  # one

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
FX = ROOT / "tests" / "fixtures" / "results"
CASES = FX / "cases"

# Never through a cached compile: CPython validates a .pyc on (mtime in whole
# seconds, source size), and a same-size deliberate break inside one second is
# served the PREVIOUS compile. See scripts/check-cost.py for the reading that
# found this. These gates exist to be broken on purpose, so it matters here.
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("fold_results", HERE / "fold-results.py")
fold_results = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(fold_results)


class Args:
    """The argparse namespace fold() expects, built from a case's args.json."""

    def __init__(self, case_dir: Path, raw: dict):
        self.environment = raw["environment"]
        self.run_id = raw.get("run_id", "fixture")
        self.workflow = raw.get("workflow", "fixture")
        self.run_url = raw.get("run_url")
        self.junit = [
            f"{pair.split('=', 1)[0]}={case_dir / pair.split('=', 1)[1]}"
            for pair in raw.get("junit", [])
        ]
        self.playwright = str(case_dir / raw["playwright"]) if raw.get("playwright") else None
        self.db_log = str(case_dir / raw["db_log"]) if raw.get("db_log") else None
        self.inventory = str(FX / "inventory.json")
        self.topology = str(FX / "topology.json")


def summarise(folded: dict) -> dict:
    nodes = {}
    for node_id, node in folded["nodes"].items():
        entry = {"status": node["status"]}
        for key, value in node["counts"].items():
            if value:
                entry[key] = value
        nodes[node_id] = entry
    return {
        "nodes": nodes,
        "unobserved": folded["unobserved"],
        "unknown": folded["unknown"],
    }


def compare(expected: dict, got: dict) -> list[str]:
    """Expected is a SUBSET check on counts and an exact one on the lists."""
    findings = []
    for node_id, want in expected.get("nodes", {}).items():
        if node_id not in got["nodes"]:
            findings.append(f"expected node {node_id}, the fold produced none")
            continue
        have = got["nodes"][node_id]
        for key, value in want.items():
            if have.get(key, 0) != value:
                findings.append(f"{node_id}.{key}: expected {value}, got {have.get(key, 0)}")
    for node_id in got["nodes"]:
        if node_id not in expected.get("nodes", {}):
            findings.append(f"the fold produced node {node_id}, which the case does not expect")
    if got["unobserved"] != expected.get("unobserved", []):
        findings.append(f"unobserved: expected {expected.get('unobserved', [])}, got {got['unobserved']}")
    if got["unknown"] != expected.get("unknown", {}):
        findings.append(f"unknown: expected {expected.get('unknown', {})}, got {got['unknown']}")
    return findings


def run_case(case_dir: Path) -> list[str]:
    raw = json.loads((case_dir / "args.json").read_text())
    expected = json.loads((case_dir / "expected.json").read_text())
    args = Args(case_dir, raw)

    if "refusal" in expected:
        try:
            with redirect_stdout(io.StringIO()):
                fold_results.fold(args)
        except fold_results.Refusal as e:
            if expected["refusal"] in str(e):
                return []
            return [f"refused, but not for the expected reason:\n    expected: {expected['refusal']}\n    got:      {e}"]
        return ["expected a refusal, the fold returned a result"]

    try:
        with redirect_stdout(io.StringIO()):
            folded = fold_results.fold(args)
    except fold_results.Refusal as e:
        return [f"unexpected refusal: {e}"]
    return compare(expected, summarise(folded))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--case", help="run one case by directory name")
    args = p.parse_args()

    if not CASES.is_dir():
        print(f"results-check: REFUSED\n{CASES.relative_to(ROOT)} does not exist.")
        return 1
    dirs = sorted(d for d in CASES.iterdir() if d.is_dir())
    if args.case:
        dirs = [d for d in dirs if d.name == args.case]
        if not dirs:
            print(f"results-check: REFUSED\nno case named {args.case}")
            return 1
    if not dirs:
        # The empty-discovery refusal this repository writes everywhere: a
        # checker that found no cases prints the same "ok" as one that passed
        # them all.
        print("results-check: REFUSED\nno cases found. A gate with nothing to check is not a green gate.")
        return 1

    failed = 0
    for case_dir in dirs:
        findings = run_case(case_dir)
        if findings:
            failed += 1
            print(f"FAIL  {case_dir.name}")
            for f in findings:
                print(f"      {f}")
        else:
            print(f"ok    {case_dir.name}")

    if failed:
        print(f"\nresults-check: {failed} of {len(dirs)} cases disagree with the fold")
        return 1
    print(f"\n{len(dirs)}/{len(dirs)} result fixtures fold as expected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
