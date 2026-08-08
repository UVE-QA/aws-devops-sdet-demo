#!/usr/bin/env python3
"""Join a folded timeline onto the map's nodes, and say what could not be joined.

    scripts/tf-stream.sh      captures terraform's own -json event stream
    scripts/fold-timeline.py  folds the streams into one timeline per run
    this script               turns that timeline into node states for the map
    publish-status.sh         publishes them beside the timeline

WHY THIS IS PYTHON AND NOT THE PAGE
-----------------------------------
The join could have lived in `assets/index.template.html`, which already fetches
`data/topology.json` and could fetch a timeline beside it. It does not, for one
reason: the rule below would then exist in JavaScript on the page and in Python
in whatever gate checked it, which is this repository's `docker compose config
--images` trap almost exactly — one definition, two hosts, and the two agreeing
right up until the moment they do not.

So the join happens once, on the runner, and the page is left a renderer. What
it fetches is already node states; the only thing it decides is how to draw
them.

THE RULE, IN FULL
-----------------
Terraform reports RESOURCES; the map draws SERVICES (ADR-0039 D5). Every
observed resource address is classified into exactly one of four buckets, and
the last two are the reason this script prints anything at all:

    a node          the address is in some node's `members`, for this
                    environment. `module.rds.aws_db_instance.this[0]` matches
                    the member `module.rds.aws_db_instance.this`: every `[...]`
                    is stripped before comparison, because count and for_each
                    are properties of an apply and `members` comes from a static
                    read of infra/
    the destroy     action `delete`. The destroy nodes are whole levels rather
    node            than groups — `destroy.stage` stands for all thirty blocks —
                    so a delete is matched by environment, not by address
    not shown       the address belongs to a group the map deliberately does not
                    draw (ADR-0039 D1). Recorded, quiet, and counted
    a data source   action `read`. Terraform emits apply_start/apply_complete
                    for DATA SOURCES too, once per invocation, and a data block
                    is not a resource block: generate-topology.py counts
                    `resource`, and D1's coverage gate is about resource blocks.
                    So a data source can never belong to a display group, and
                    reporting it as unknown would be a permanent false positive
                    in the one channel that is supposed to be rare. Found on the
                    first live teardown - no fixture had a data source in it
    unknown         nothing claims it. LOUD: printed, counted, and carried into
                    the published file, because a resource that a cycle created
                    and the map does not draw is precisely the silence D1 exists
                    to end

WHAT A NODE'S NUMBERS MEAN
--------------------------
    duration_s      first `apply_start` in the group to the last
                    `apply_complete` — the node is busy while ANY of its
                    resources is in flight (ADR-0039 D5, the middle row). This
                    is exact, not an approximation
    identifier      the `id_value` of the member that took the LONGEST, when it
                    carries one. Not a hand-written "for RDS, show the
                    instance": a table like that would be a claim, and this is
                    derived — the resource that dominates a node's duration is
                    the one the node is mostly about. Nothing is enriched into
                    anything, and no AWS call is made (ADR-0039 D2)

There is no cost here. Cost is 20d, it needs a dated rate table, and it renders
labelled COMPUTED (ADR-0039 D3).

Usage:
    scripts/node-states.py --topology site/data/topology.json \\
        --timeline /tmp/timeline-stage.json --out /tmp/nodes-stage.json

Exit status is 0 whenever the join itself succeeded, INCLUDING when addresses
went unmatched. Same reason as the fold: this step reports, it does not judge,
and a non-zero here would take down the publish of the very run that needed
looking at. It exits non-zero only when it cannot do its own job — an unreadable
input, an unwritable --out.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "node-states/1"

# Every `[...]` in an address, at any position. Two shapes appear:
#   module.network.aws_subnet.public[0]   count on the resource
#   module.pair[0].terraform_data.only    count on the module
# infra/ has only the first today. The second is covered because a rule written
# for a shape nobody exercised is the class of thing this repository breaks on
# purpose — tests/fixtures/timeline/cases/apply-module has both.
INDEX = re.compile(r"\[[^\]]*\]")


def base_address(addr: str) -> str:
    return INDEX.sub("", addr or "")


def parse_ts(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def iso(dt) -> str | None:
    if dt is None:
        return None
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def seconds_between(a, b):
    if a is None or b is None:
        return None
    return round((b - a).total_seconds(), 1)


def cycle_kind(timeline: dict) -> str:
    """apply or destroy, taken from what was RUN, not from what was reached.

    `command` is fold-timeline's already-resolved answer: the argv of the
    invocation beats whatever the stream got as far as saying, because an apply
    killed before it finishes emits a change_summary whose operation is "plan".
    """
    commands = {op.get("command") for op in timeline.get("operations", [])}
    return "destroy" if "destroy" in commands else "apply"


def index_members(topology: dict, environment: str) -> dict[str, str]:
    """Normalised member address -> node id, for ONE environment.

    Filtering by environment is not tidiness. `stage.vpc` and `prod.vpc` hold
    the SAME member addresses — they are the same modules in two state levels —
    so an index built across both would map every address to whichever node was
    seen last, and half the map would light from the other environment's cycle.
    """
    index: dict[str, str] = {}
    for phase in topology.get("phases", []):
        for node in phase.get("nodes", []):
            if node.get("env") != environment:
                continue
            for member in node.get("members", []) or []:
                index[base_address(member)] = node["id"]
    return index


def index_hidden(topology: dict) -> dict[str, str]:
    """Normalised address -> the group that deliberately does not draw it."""
    index: dict[str, str] = {}
    for group in topology.get("not_shown", []):
        for member in group.get("members", []) or []:
            index[base_address(member)] = group["group"]
    return index


def phase_of(topology: dict, environment: str) -> dict[str, str]:
    """node id -> the phase that draws it, for this environment."""
    index: dict[str, str] = {}
    for phase in topology.get("phases", []):
        for node in phase.get("nodes", []):
            if node.get("env") == environment:
                index[node["id"]] = phase["id"]
    return index


def destroy_node(topology: dict, environment: str) -> str | None:
    for phase in topology.get("phases", []):
        for node in phase.get("nodes", []):
            if node.get("service") == "destroy" and node.get("env") == environment:
                return node["id"]
    return None


def join(topology: dict, timeline: dict) -> dict:
    environment = timeline.get("environment")
    kind = cycle_kind(timeline)
    members = index_members(topology, environment)
    hidden = index_hidden(topology)
    teardown = destroy_node(topology, environment)

    collected: dict[str, list[dict]] = {}
    not_shown: list[str] = []
    reads: list[str] = []
    unknown: list[str] = []
    matched = 0

    for op in timeline.get("operations", []):
        for resource in op.get("resources", []):
            address = resource.get("address") or ""
            base = base_address(address)
            if resource.get("action") == "read":
                # A data source. Checked BEFORE anything else, because the
                # address of one looks like any other and the action is the
                # only thing that distinguishes it.
                reads.append(address)
                continue
            if resource.get("action") == "delete":
                node_id = teardown
            else:
                node_id = members.get(base)
            if node_id:
                collected.setdefault(node_id, []).append(resource)
                matched += 1
                continue
            if base in hidden:
                not_shown.append(address)
                continue
            unknown.append(address)

    nodes = {}
    for node_id, resources in collected.items():
        starts = [parse_ts(r.get("started_at")) for r in resources]
        ends = [parse_ts(r.get("finished_at")) for r in resources]
        starts = [s for s in starts if s]
        ends = [e for e in ends if e]
        complete = [r for r in resources if r.get("status") == "complete"]

        # The member that took the longest, among those that finished and
        # carry an identity. `elapsed_seconds` is terraform's own figure.
        dominant = None
        for resource in complete:
            if not resource.get("id_value"):
                continue
            if dominant is None or (resource.get("elapsed_seconds") or 0) > (
                dominant.get("elapsed_seconds") or 0
            ):
                dominant = resource

        nodes[node_id] = {
            # A node is measured only when every member of it finished. The
            # published file is written from a COMPLETE timeline anyway, so
            # this is belt as well as braces - but a node quietly reporting a
            # duration that stops in the middle of itself is exactly the
            # plausible-looking half-truth 20b.1 was about.
            "state": "measured" if len(complete) == len(resources) else "incomplete",
            "duration_s": seconds_between(min(starts), max(ends)) if starts and ends else None,
            "identifier": dominant.get("id_value") if dominant else None,
            "identifier_from": dominant.get("address") if dominant else None,
            "resources_observed": len(resources),
            "resources_complete": len(complete),
        }

    # The same span, one level up: a phase is busy from the first apply_start
    # among ALL its nodes to the last apply_complete. Computed here rather than
    # on the page for the reason the whole join is here - and it could not be
    # done there at all, because a node reports its duration and not its
    # boundaries, and durations of overlapping things do not add up.
    phase_index = phase_of(topology, environment)
    phases: dict[str, dict] = {}
    for node_id, resources in collected.items():
        phase_id = phase_index.get(node_id)
        if not phase_id:
            continue
        starts = [parse_ts(r.get("started_at")) for r in resources]
        ends = [parse_ts(r.get("finished_at")) for r in resources]
        starts = [s for s in starts if s]
        ends = [e for e in ends if e]
        if not starts or not ends:
            continue
        entry = phases.setdefault(phase_id, {"first": None, "last": None, "nodes": 0})
        entry["nodes"] += 1
        low, high = min(starts), max(ends)
        if entry["first"] is None or low < entry["first"]:
            entry["first"] = low
        if entry["last"] is None or high > entry["last"]:
            entry["last"] = high
    phases = {
        pid: {
            "duration_s": seconds_between(e["first"], e["last"]),
            "started_at": iso(e["first"]),
            "finished_at": iso(e["last"]),
            "nodes": e["nodes"],
        }
        for pid, e in sorted(phases.items())
    }

    started = parse_ts(timeline.get("started_at"))
    return {
        "schema": SCHEMA,
        "environment": environment,
        "kind": kind,
        "written_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "cycle": {
            "status": timeline.get("status"),
            "date": started.date().isoformat() if started else None,
            "started_at": timeline.get("started_at"),
            "finished_at": timeline.get("finished_at"),
            "duration_seconds": timeline.get("duration_seconds"),
            "tool": timeline.get("tool"),
            "run": timeline.get("run"),
        },
        # The counts are of the DEDUPLICATED lists below, because those are what
        # a reader acts on. They disagreed on the first live teardown - two
        # events for one data source read as "unknown: 2" above a list naming
        # one address - and a count that does not match the thing under it is
        # the class of defect ADR-0039 D1 exists to remove.
        "observed": {
            "resources": matched + len(set(not_shown)) + len(set(reads)) + len(set(unknown)),
            "matched": matched,
            "not_shown": len(set(not_shown)),
            "read": len(set(reads)),
            "unknown": len(set(unknown)),
            "nodes": len(nodes),
        },
        "not_shown": sorted(set(not_shown)),
        "read": sorted(set(reads)),
        "unknown": sorted(set(unknown)),
        "phases": phases,
        "nodes": dict(sorted(nodes.items())),
    }


def render(states: dict, out=None) -> None:
    stream = sys.stdout if out is None else out

    def line(text=""):
        print(text, file=stream)

    o = states["observed"]
    line(f"node states: {states['environment']} — {states['kind']} — "
         f"{states['cycle']['status'].upper() if states['cycle']['status'] else 'UNKNOWN'}")
    line(f"  {o['resources']} observed → {o['nodes']} nodes; {o['matched']} matched, "
         f"{o['not_shown']} not shown, {o['read']} data sources, {o['unknown']} unknown")
    line()
    if states["nodes"]:
        width = max(len(n) for n in states["nodes"])
        line(f"  {'node'.ljust(width)}  {'secs':>6}  {'state':<10} identifier")
        for node_id, node in states["nodes"].items():
            secs = "-" if node["duration_s"] is None else f"{node['duration_s']:.0f}"
            line(f"  {node_id.ljust(width)}  {secs:>6}  {node['state']:<10} "
                 f"{node['identifier'] or ''}")
        line()

    # Printed even when empty is wrong, and printed only when non-empty is what
    # makes it findable: an UNKNOWN line in an apply log is the signal that the
    # map has stopped describing what the cycle does.
    if states["not_shown"]:
        line(f"  not shown ({len(states['not_shown'])}), by decision:")
        for address in states["not_shown"]:
            line(f"    {address}")
        line()
    if states["unknown"]:
        line(f"  UNKNOWN ({len(states['unknown'])}) — observed in this cycle and on no node:")
        for address in states["unknown"]:
            line(f"    {address}")
        line("  The map does not draw these. Assign them in assets/topology-groups.json.")
        line()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--topology", required=True, type=Path)
    parser.add_argument("--timeline", required=True, type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    if not args.timeline.is_file():
        # Not an error, for the same reason the fold is not: a run can fail
        # before terraform ever ran, and there is nothing to join.
        print(f"no timeline at {args.timeline}: no node states written")
        return 0

    topology = json.loads(args.topology.read_text(encoding="utf-8"))
    timeline = json.loads(args.timeline.read_text(encoding="utf-8"))
    states = join(topology, timeline)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(states, indent=2) + "\n", encoding="utf-8")

    if not args.quiet:
        render(states)
        if args.out:
            print(f"node states written to {args.out}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
