#!/usr/bin/env python3
"""What a cycle cost, COMPUTED from how long its resources existed.

    scripts/fold-timeline.py   folds terraform's event stream into a timeline
    scripts/fetch-rates.py     captures the prices
    scripts/sizing.py          reads the shape out of infra/
    this script                multiplies the three and says how sure it is not

THE MISTAKE THIS FILE EXISTS TO AVOID
-------------------------------------
A timeline carries `elapsed_seconds` per resource, and it is the obvious number
to multiply by a rate. It is the wrong number. `elapsed_seconds` is how long
TERRAFORM took to create the thing; the meter runs for as long as the thing
EXISTS. In the cycle of 2026-08-08 the RDS instance took 297 seconds to create
and then stood for another 852 before the teardown touched it — an estimate built
on the creation figure would have been low by a factor of four, and would have
looked entirely reasonable.

So the meter is a LIFETIME, and a lifetime spans two runs: the apply that created
the resource and the destroy that removed it. Both are published; this script
takes both.

WHY IT IS A BAND AND NOT A NUMBER
---------------------------------
Terraform reports when it STARTED creating a resource and when it FINISHED. AWS
starts charging somewhere in between — for an ALB when the load balancer is
provisioned, for RDS when the instance reaches `available` — and the event stream
cannot see which instant. The same ambiguity closes the window at the other end.
Rather than pick one and call it the answer, both are computed:

    low     create FINISHED -> delete STARTED     the resource certainly existed
    high    create STARTED  -> delete FINISHED    it certainly did not exist longer

For a cheap resource the two are within a few per cent. For RDS in that cycle
they were 852 and 1381 seconds — a 62% spread, and a single figure would have
hidden a real uncertainty behind two decimal places. ADR-0026's rule about state
applies to money: say what was observed, and say what was inferred.

WHAT IT DOES NOT CLAIM
----------------------
It is an ESTIMATE and it says so in every rendering. It is not a bill, no Cost
Explorer credential is involved, and no AWS call is made here at all — the inputs
are two JSON files and the repository (ADR-0045).

Usage:
    scripts/fold-cost.py --environment stage \\
        --apply /tmp/timeline-apply.json --destroy /tmp/timeline-destroy.json \\
        --out /tmp/cost-stage.json
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from sizing import Refusal, environment_shape  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCHEMA = "cost/1"
HOURS_PER_MONTH = 730  # AWS's own convention for converting a GB-month price


class Refused(Exception):
    pass


def parse_ts(value):
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def iso(moment):
    return None if moment is None else moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def span(start, end) -> float:
    if start is None or end is None:
        return 0.0
    return max(0.0, (end - start).total_seconds())


def overlap(a_start, a_end, b_start, b_end) -> float:
    if None in (a_start, a_end, b_start, b_end):
        return 0.0
    lo = max(a_start, b_start)
    hi = min(a_end, b_end)
    return max(0.0, (hi - lo).total_seconds())


def resources_of(timeline: dict, actions: set[str]) -> dict:
    found = {}
    for operation in timeline.get("operations", []):
        for resource in operation.get("resources", []):
            if resource.get("action") not in actions:
                continue
            found[resource["address"]] = resource
    return found


def component_cost(component: dict, unit_prices: dict, shape: dict, seconds: float) -> float:
    key = component["unit_price"]
    price = unit_prices.get(key)
    if price is None:
        raise Refused(f"the cost model prices something with '{key}', which the rate table has not captured")
    quantity = component.get("quantity", 1)
    for name in component.get("quantity_from", []):
        if name not in shape:
            raise Refused(f"the cost model asks for '{name}', which the configuration does not report")
        quantity *= shape[name]
    hours = seconds / 3600.0
    if component.get("per") == "month":
        hours = hours / HOURS_PER_MONTH
    return quantity * float(price["usd"]) * hours


def pairing_refusals(environment, apply_timeline, destroy_timeline) -> list[str]:
    """Why these two timelines cannot be the two halves of one cycle.

    A lifetime spans two runs, so this fold is the only thing here that takes
    input from two of them — and until 20f it believed whatever it was handed.
    That is worse than it sounds. A mismatched pair does not crash: `span()`
    clamps a negative lifetime to zero, so the fold returns a small, plausible,
    entirely wrong figure. A defect that answers is more expensive than one that
    stops.

    Four clauses. The fourth is deliberately WEAK, and the weakness is the
    decision: ADR-0038 adopts orphaned resources into the state before a
    teardown, so a destroy legitimately removes things its apply never created —
    `tests/fixtures/cost/cases/a-delete-with-no-create-is-named` is that case,
    and it stays green here. Only a teardown with NOTHING in common with the
    apply is refused.
    """
    problems = []

    # fold-timeline.py always writes `environment`, so a timeline without one did
    # not come from this project. Refusing the absence rather than skipping the
    # check: an unchecked field reads exactly like a passing one.
    for role, timeline in (("apply", apply_timeline), ("destroy", destroy_timeline)):
        if timeline is None:
            continue
        named = timeline.get("environment")
        if named is None:
            problems.append(f"the {role} timeline names no environment")
        elif named != environment:
            problems.append(f"the {role} timeline is {named}, not {environment}")

    if apply_timeline.get("status") != "complete":
        # A partial apply priced against a full teardown reports lifetimes for
        # the resources terraform reached and silence for the ones it did not.
        problems.append(
            f"the apply timeline is {apply_timeline.get('status')!r}, and only a complete "
            "apply knows everything the teardown is removing")

    if destroy_timeline is None:
        return problems

    apply_end = parse_ts(apply_timeline.get("finished_at"))
    destroy_start = parse_ts(destroy_timeline.get("started_at"))
    if apply_end and destroy_start and destroy_start < apply_end:
        problems.append(
            f"the teardown started at {iso(destroy_start)}, before the apply finished at "
            f"{iso(apply_end)}")

    created = set(resources_of(apply_timeline, {"create", "replace"}))
    deleted = set(resources_of(destroy_timeline, {"delete"}))
    if deleted and not (created & deleted):
        problems.append(
            f"the teardown deleted {len(deleted)} resource(s) and this apply created none of "
            "them")

    return problems


def build(environment, apply_timeline, destroy_timeline, rates, model, shape, as_of) -> dict:
    problems = pairing_refusals(environment, apply_timeline, destroy_timeline)
    if problems:
        raise Refused("these timelines are not one cycle: " + "; ".join(problems))

    unit_prices = rates.get("unit_prices", {})
    created = resources_of(apply_timeline, {"create", "replace"})
    deleted = resources_of(destroy_timeline, {"delete"}) if destroy_timeline else {}

    closed = destroy_timeline is not None
    rows = []
    unpriced = []
    orphan_deletes = sorted(set(deleted) - set(created))

    total_low = total_high = 0.0
    for address, resource in created.items():
        kind = resource.get("type")
        row = {
            "address": address,
            "type": kind,
            "created": {"started_at": resource.get("started_at"),
                        "finished_at": resource.get("finished_at")},
            "deleted": None,
            "bucket": None,
            "state": None,
            "seconds": {"low": None, "high": None},
            "usd": {"low": None, "high": None},
        }

        if kind in model.get("free", {}):
            row["bucket"] = "free"
            row["state"] = "free"
            row["reason"] = model["free"][kind]
            rows.append(row)
            continue
        if kind in model.get("not_metered", {}):
            row["bucket"] = "not_metered"
            row["state"] = "not_metered"
            row["reason"] = model["not_metered"][kind]
            rows.append(row)
            continue
        priced = model.get("priced", {}).get(kind)
        if priced is None:
            row["bucket"] = "unpriced"
            row["state"] = "unpriced"
            unpriced.append(address)
            rows.append(row)
            continue

        create_started = parse_ts(resource.get("started_at"))
        create_finished = parse_ts(resource.get("finished_at"))
        delete_record = deleted.get(address)
        if delete_record is not None:
            row["deleted"] = {"started_at": delete_record.get("started_at"),
                              "finished_at": delete_record.get("finished_at")}
            low_end = parse_ts(delete_record.get("started_at"))
            high_end = parse_ts(delete_record.get("finished_at"))
            row["state"] = "closed"
        else:
            low_end = high_end = as_of
            row["state"] = "open" if not closed else "never_deleted"

        low = span(create_finished, low_end)
        high = span(create_started, high_end)
        minimum = priced.get("minimum_seconds", 0)
        low, high = max(low, minimum), max(high, minimum)

        usd_low = sum(component_cost(c, unit_prices, shape, low) for c in priced["components"])
        usd_high = sum(component_cost(c, unit_prices, shape, high) for c in priced["components"])

        row["bucket"] = "priced"
        row["seconds"] = {"low": round(low, 1), "high": round(high, 1)}
        row["usd"] = {"low": round(usd_low, 6), "high": round(usd_high, 6)}
        row["minimum_seconds_applied"] = bool(minimum and low <= minimum)

        # THE RATE, so an OPEN row can be re-priced by a reader without owning
        # the model (ADR-0067). component_cost() is linear in `seconds` - every
        # component is quantity x unit price x hours - so one number per second
        # is the whole of this resource's pricing, and a page multiplying it by
        # its own clock reproduces this function exactly.
        #
        # It is published for OPEN rows only. A closed row has both ends and a
        # figure that is finished; handing a rate to a reader who does not need
        # one invites re-deriving a number that is already correct.
        #
        # `minimum_seconds` is where the linearity stops: below it the fold
        # charges the floor, so a rate multiplied by a smaller elapsed would
        # UNDERSTATE. The flag beside it says when that is in play, and the
        # per-second figure is omitted entirely in that case rather than
        # published with a caveat nobody downstream is obliged to read.
        if row["state"] == "open" and not row["minimum_seconds_applied"]:
            per_second = sum(
                component_cost(c, unit_prices, shape, 1.0) for c in priced["components"]
            )
            row["usd_per_second"] = round(per_second, 12)
        if priced.get("note"):
            row["note"] = priced["note"]
        total_low += usd_low
        total_high += usd_high
        rows.append(row)

    cycle_start = parse_ts(apply_timeline.get("started_at"))
    cycle_end = parse_ts(destroy_timeline.get("finished_at")) if closed else as_of

    return {
        "_comment": (
            "COMPUTED by scripts/fold-cost.py from resource LIFETIMES and a dated rate "
            "table. An estimate, expressed as a band, and not a bill: no billing API is "
            "consulted anywhere in this project (ADR-0045)."
        ),
        "schema": SCHEMA,
        "environment": environment,
        "kind": "computed_estimate",
        "written_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rates": {
            "captured_at": rates.get("captured_at"),
            "region": rates.get("region"),
            "source": rates.get("source"),
        },
        "shape": shape,
        "cycle": {
            "status": "closed" if closed else "open",
            "started_at": iso(cycle_start),
            "finished_at": iso(cycle_end),
            "duration_seconds": round(span(cycle_start, cycle_end), 1),
            "apply_run": apply_timeline.get("run"),
            "destroy_run": destroy_timeline.get("run") if closed else None,
            "usd": {"low": round(total_low, 6), "high": round(total_high, 6)},
        },
        "counts": {
            "created": len(created),
            "priced": sum(1 for r in rows if r["bucket"] == "priced"),
            "free": sum(1 for r in rows if r["bucket"] == "free"),
            "not_metered": sum(1 for r in rows if r["bucket"] == "not_metered"),
            "unpriced": len(unpriced),
            "orphan_deletes": len(orphan_deletes),
        },
        "unpriced": unpriced,
        "orphan_deletes": orphan_deletes,
        "resources": rows,
    }


def attribute_to_phases(cost: dict, phase_windows: dict) -> dict:
    """Where in the cycle the money accrued, by OVERLAP with each phase's window.

    A phase is a window of a RUN and a charge is a window of a LIFETIME, so the
    honest join is how much of each lifetime fell inside each phase — not "which
    phase created this resource", which would put an ALB's whole half-hour onto
    the two minutes that made it.

    The interesting bucket is the last one. Most of a cycle's money is spent
    while no phase is running at all: the environment is up, the demo is being
    looked at, and nothing is deploying.
    """
    buckets = {name: 0.0 for name in phase_windows}
    outside = 0.0
    for row in cost["resources"]:
        if row["bucket"] != "priced" or not row["usd"]["low"]:
            continue
        start = parse_ts(row["created"]["finished_at"])
        end = parse_ts((row["deleted"] or {}).get("started_at")) if row["deleted"] else None
        if end is None:
            end = parse_ts(cost["cycle"]["finished_at"])
        lifetime = span(start, end)
        if lifetime <= 0:
            continue
        rate = row["usd"]["low"] / lifetime
        covered = 0.0
        for name, (window_start, window_end) in phase_windows.items():
            seconds = overlap(start, end, window_start, window_end)
            buckets[name] += seconds * rate
            covered += seconds
        outside += max(0.0, lifetime - covered) * rate

    return {
        "_comment": "Overlap attribution, low bound only. The phases do not cover the "
                    "cycle: the gap between them is when the environment is simply up.",
        "phases": {name: round(value, 6) for name, value in sorted(buckets.items())},
        "outside_any_phase": round(outside, 6),
    }


def phase_windows_from(nodes_files: list[pathlib.Path]) -> dict:
    windows = {}
    for path in nodes_files:
        states = json.loads(path.read_text(encoding="utf-8"))
        kind = states.get("kind", path.stem)
        for phase_id, phase in (states.get("phases") or {}).items():
            start, end = parse_ts(phase.get("started_at")), parse_ts(phase.get("finished_at"))
            if start and end:
                windows[f"{kind}:{phase_id}"] = (start, end)
    return windows


def render(cost: dict, out=None) -> None:
    stream = sys.stdout if out is None else out

    def line(text=""):
        print(text, file=stream)

    c = cost["cycle"]
    line(f"cost: {cost['environment']} — COMPUTED ESTIMATE, not a bill")
    line(f"  rates captured {cost['rates']['captured_at']} for {cost['rates']['region']}")
    line(f"  cycle {c['status'].upper()}  {c['started_at']} -> {c['finished_at']}  "
         f"({c['duration_seconds']:.0f}s)")
    line(f"  ESTIMATE  ${c['usd']['low']:.4f} .. ${c['usd']['high']:.4f}")
    line()
    priced = [r for r in cost["resources"] if r["bucket"] == "priced"]
    if priced:
        width = max(len(r["address"]) for r in priced)
        line(f"  {'resource'.ljust(width)}  {'low s':>7} {'high s':>7}  "
             f"{'low $':>10} {'high $':>10}  state")
        for row in priced:
            line(f"  {row['address'].ljust(width)}  {row['seconds']['low']:>7.0f} "
                 f"{row['seconds']['high']:>7.0f}  {row['usd']['low']:>10.4f} "
                 f"{row['usd']['high']:>10.4f}  {row['state']}")
        line()
    k = cost["counts"]
    line(f"  {k['created']} created: {k['priced']} priced, {k['free']} free, "
         f"{k['not_metered']} not metered, {k['unpriced']} UNPRICED")
    for address in cost["unpriced"]:
        line(f"    UNPRICED  {address}")
    for address in cost["orphan_deletes"]:
        line(f"    DELETED BUT NEVER CREATED IN THIS APPLY  {address}")
    if cost.get("attribution"):
        line()
        line("  where it accrued (low bound):")
        for name, value in cost["attribution"]["phases"].items():
            line(f"    {name:<28} ${value:.4f}")
        line(f"    {'outside any phase':<28} ${cost['attribution']['outside_any_phase']:.4f}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--apply", required=True, type=pathlib.Path)
    parser.add_argument("--destroy", type=pathlib.Path)
    parser.add_argument("--rates", type=pathlib.Path, default=ROOT / "site/data/rates.json")
    parser.add_argument("--model", type=pathlib.Path, default=ROOT / "assets/cost-model.json")
    parser.add_argument("--env-dir", type=pathlib.Path,
                        help="infra directory the shape is read from; defaults to "
                             "infra/envs/<environment>")
    parser.add_argument("--nodes", type=pathlib.Path, action="append", default=[],
                        help="a node-states file, for phase attribution. Repeatable.")
    parser.add_argument("--as-of", help="UTC instant an OPEN cycle is priced to "
                                        "(YYYY-MM-DDTHH:MM:SSZ). Defaults to now.")
    parser.add_argument("--out", type=pathlib.Path)
    args = parser.parse_args()

    try:
        apply_timeline = json.loads(args.apply.read_text(encoding="utf-8"))
        destroy_timeline = (json.loads(args.destroy.read_text(encoding="utf-8"))
                            if args.destroy else None)
        rates = json.loads(args.rates.read_text(encoding="utf-8"))
        model = json.loads(args.model.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2

    env_dir = args.env_dir or (ROOT / "infra/envs" / args.environment)
    try:
        shape = environment_shape(env_dir)
    except Refusal as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    shape = {k: v for k, v in shape.items() if k != "from"} | {"from": shape["from"]}

    as_of = parse_ts(args.as_of) if args.as_of else datetime.now(timezone.utc).replace(microsecond=0)

    try:
        cost = build(args.environment, apply_timeline, destroy_timeline, rates, model,
                     shape, as_of)
    except Refused as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2

    if args.nodes:
        cost["attribution"] = attribute_to_phases(cost, phase_windows_from(args.nodes))

    render(cost)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(cost, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
