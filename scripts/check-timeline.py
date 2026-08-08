#!/usr/bin/env python3
"""The gate over scripts/fold-timeline.py.

Folds every case under tests/fixtures/timeline/cases/ and compares the result
against that case's expected.json. Runs in ci.yml; costs nothing and calls no
AWS.

The claim it defends is one sentence: **a run that dies mid-apply must produce a
timeline marked INCOMPLETE, never a plausible complete one.** Everything else
here exists so that claim cannot be true by accident — a fold that marked
everything incomplete would satisfy it and be useless, so the complete and
errored cases are checked just as exactly.

What is compared is a summary, not the whole timeline: statuses, counts,
resource verdicts, diagnostic counts, and the health of the stream itself. Not
timestamps, ids or durations - those differ on every generation, and a gate that
had to be regenerated after every run would be turned off within a week.

    scripts/check-timeline.py                      # all cases
    scripts/check-timeline.py --case apply-killed  # one

Exit status: 0 if every case matches, 1 otherwise.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

import importlib.util

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CASES = ROOT / "tests" / "fixtures" / "timeline" / "cases"

spec = importlib.util.spec_from_file_location("fold_timeline", HERE / "fold-timeline.py")
fold_timeline = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(fold_timeline)


def summarise(timeline: dict) -> dict:
    operations = []
    for op in timeline["operations"]:
        verdicts = {"complete": 0, "errored": 0, "incomplete": 0}
        for resource in op["resources"]:
            verdicts[resource["status"]] = verdicts.get(resource["status"], 0) + 1
        severities = {"error": 0, "warning": 0}
        for diag in op["diagnostics"]:
            key = "error" if diag["severity"] == "error" else "warning"
            severities[key] += 1
        operations.append(
            {
                "label": op["label"],
                "command": op["command"],
                "status": op["status"],
                "exit_code": op["exit_code"],
                "resources": verdicts,
                "diagnostics": severities,
                "stream": {
                    "unparsed_lines": op["stream"]["unparsed_lines"],
                    "unknown_types": sorted(op["stream"]["unknown_types"]),
                },
            }
        )
    return {
        "status": timeline["status"],
        "totals": {
            "operations": timeline["totals"]["operations"],
            "resources_created": timeline["totals"]["resources_created"],
            "resources_destroyed": timeline["totals"]["resources_destroyed"],
        },
        "operations": operations,
    }


def diff(expected, actual, path="") -> list[str]:
    problems: list[str] = []
    if isinstance(expected, dict) and isinstance(actual, dict):
        for key in expected:
            if key not in actual:
                problems.append(f"{path}.{key}: missing from the folded timeline")
            else:
                problems += diff(expected[key], actual[key], f"{path}.{key}")
        return problems
    if isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            problems.append(f"{path}: expected {len(expected)} item(s), folded {len(actual)}")
            return problems
        for index, (exp, act) in enumerate(zip(expected, actual)):
            problems += diff(exp, act, f"{path}[{index}]")
        return problems
    if expected != actual:
        problems.append(f"{path}: expected {expected!r}, folded {actual!r}")
    return problems


def check_case(case_dir: Path) -> tuple[bool, list[str]]:
    expected_path = case_dir / "expected.json"
    streams = case_dir / "streams"
    if not expected_path.exists():
        return False, [f"{case_dir.name}: no expected.json"]
    if not streams.is_dir() or not list(streams.glob("*.jsonl")):
        return False, [f"{case_dir.name}: no streams to fold"]

    expected = json.loads(expected_path.read_text())
    expected.pop("description", None)

    operations = fold_timeline.collect_streams(streams)
    for op in operations:
        op.read()
    timeline = fold_timeline.build(case_dir.name, operations, fold_timeline.github_run())

    problems = diff(expected, summarise(timeline), case_dir.name)

    # The readable log is not optional (ADR-0039 D2), so it is exercised here
    # too: it must render without raising, and every error diagnostic must
    # appear in it. A summary that silently dropped the reason for a failure
    # would be worse than no summary at all.
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        fold_timeline.render(timeline)
    rendered = buffer.getvalue()
    if timeline["status"].upper() not in rendered:
        problems.append(f"{case_dir.name}: the readable log does not state the status")
    for op in timeline["operations"]:
        for diagnostic in op["diagnostics"]:
            if diagnostic["severity"] != "error":
                continue
            if str(diagnostic["summary"]) not in rendered:
                problems.append(
                    f"{case_dir.name}: error diagnostic "
                    f"{diagnostic['summary']!r} is missing from the readable log"
                )

    return not problems, problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--case", action="append", help="check only this case")
    parser.add_argument("--cases-dir", type=Path, default=CASES)
    args = parser.parse_args(argv)

    if not args.cases_dir.is_dir():
        print(f"FAIL  no fixture directory at {args.cases_dir}")
        return 1

    case_dirs = sorted(d for d in args.cases_dir.iterdir() if d.is_dir())
    if args.case:
        wanted = set(args.case)
        case_dirs = [d for d in case_dirs if d.name in wanted]
        missing = wanted - {d.name for d in case_dirs}
        if missing:
            print(f"FAIL  no such case(s): {', '.join(sorted(missing))}")
            return 1

    if not case_dirs:
        # An empty fixture directory must not read as a pass. This gate's own
        # subject is the difference between "nothing happened" and "nothing was
        # observed"; it does not get to make that mistake itself.
        print(f"FAIL  no cases under {args.cases_dir}")
        return 1

    failures = 0
    for case_dir in case_dirs:
        ok, problems = check_case(case_dir)
        if ok:
            print(f"ok    {case_dir.name}")
        else:
            failures += 1
            print(f"FAIL  {case_dir.name}")
            for problem in problems:
                print(f"        {problem}")

    print()
    print(f"{len(case_dirs) - failures}/{len(case_dirs)} timeline fixtures fold as expected")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
