#!/usr/bin/env python3
"""The gate over scripts/fold-cost.py.

Runs every case under tests/fixtures/cost/cases/ and compares the fold against
that case's expected.json. Runs in ci.yml; costs nothing, calls no AWS, and needs
no credential.

The claim it defends is one sentence: **the meter is a lifetime, not a creation,
and what cannot be metered is named rather than counted as zero.** Everything
else exists so that claim cannot be true by accident:

    a lifetime is not a creation      the real cycle of 2026-08-08, where the two
                                      differ by a factor of nine on the ALB
    the minimum binds                 a database deleted two minutes after it came
                                      up still costs ten, which is the one
                                      direction a duration-only fold can never go
    an open cycle                     no destroy timeline: the meter is open and
                                      says so, priced to an instant
    an unclassified kind              a NAT gateway nobody put in the cost model
                                      is UNPRICED and loud, not silently free
    a delete with no create           the symptom of a destroy paired with the
                                      wrong apply
    a resource never deleted          the teardown left something behind and the
                                      meter did not stop

Only the fields expected.json names are compared, like check-timeline.py: prose,
provenance and `written_at` differ per run and a gate that had to be regenerated
after every run would be turned off within a week.

    scripts/check-cost.py                                  # all cases
    scripts/check-cost.py --case a-lifetime-is-not-a-creation

Exit status: 0 if every case matches, 1 otherwise.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CASES = ROOT / "tests/fixtures/cost/cases"
RATES = ROOT / "tests/fixtures/cost/rates.json"
MODEL = ROOT / "assets/cost-model.json"


def fold_cost_module():
    spec = importlib.util.spec_from_file_location("fold_cost", ROOT / "scripts/fold-cost.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def diff(expected, actual, path="") -> list[str]:
    problems: list[str] = []
    if isinstance(expected, dict) and isinstance(actual, dict):
        for key in expected:
            if key not in actual:
                problems.append(f"{path}.{key}: missing")
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
    if isinstance(expected, float) or isinstance(actual, float):
        try:
            if abs(float(expected) - float(actual)) <= 1e-6:
                return problems
        except (TypeError, ValueError):
            pass
    if expected != actual:
        problems.append(f"{path}: expected {expected!r}, folded {actual!r}")
    return problems


def summarise(cost: dict) -> dict:
    """The parts a reader would act on: the band, the buckets, the loud lists."""
    return {
        "cycle": {
            "status": cost["cycle"]["status"],
            "usd": cost["cycle"]["usd"],
        },
        "counts": cost["counts"],
        "unpriced": cost["unpriced"],
        "orphan_deletes": cost["orphan_deletes"],
        "resources": {
            row["address"]: {
                "bucket": row["bucket"],
                "state": row["state"],
                "seconds": row["seconds"],
                "usd": row["usd"],
            }
            for row in cost["resources"]
        },
    }


def run_case(case_dir: pathlib.Path, fold_cost) -> tuple[bool, list[str]]:
    expected_path = case_dir / "expected.json"
    if not expected_path.exists():
        return False, [f"{case_dir.name}: no expected.json"]

    case = json.loads((case_dir / "case.json").read_text(encoding="utf-8"))
    apply_timeline = json.loads((case_dir / "apply.json").read_text(encoding="utf-8"))
    destroy_path = case_dir / "destroy.json"
    destroy_timeline = (json.loads(destroy_path.read_text(encoding="utf-8"))
                        if destroy_path.exists() else None)
    shape = json.loads((case_dir / "shape.json").read_text(encoding="utf-8"))
    rates = json.loads(RATES.read_text(encoding="utf-8"))
    model = json.loads(MODEL.read_text(encoding="utf-8"))

    as_of = fold_cost.parse_ts(case["as_of"]) if case.get("as_of") else None
    if as_of is None and destroy_timeline is None:
        return False, [f"{case_dir.name}: an open cycle needs an as_of, or the case is a clock"]

    cost = fold_cost.build(case["environment"], apply_timeline, destroy_timeline,
                           rates, model, shape, as_of)

    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    expected.pop("description", None)
    problems = diff(expected, summarise(cost), case_dir.name)
    return not problems, problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", help="run one case by directory name")
    args = parser.parse_args(argv)

    fold_cost = fold_cost_module()
    case_dirs = sorted(p for p in CASES.iterdir() if p.is_dir())
    if args.case:
        case_dirs = [p for p in case_dirs if p.name == args.case]
        if not case_dirs:
            print(f"no such case: {args.case}", file=sys.stderr)
            return 1
    if not case_dirs:
        print("no cost fixtures found — refusing to report zero cases as success",
              file=sys.stderr)
        return 1

    failures = 0
    for case_dir in case_dirs:
        ok, problems = run_case(case_dir, fold_cost)
        if ok:
            print(f"  ok    {case_dir.name}")
        else:
            failures += 1
            print(f"  FAIL  {case_dir.name}")
            for problem in problems:
                print(f"          {problem}")

    print(f"{len(case_dirs) - failures}/{len(case_dirs)} cost fixtures fold as expected")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
