#!/usr/bin/env python3
"""Fold Terraform's own `-json` event stream into a timeline, and back into a
readable log.

ADR-0039 D2: order and duration come from Terraform's event stream, because a
hand-written mapping from workflow step to service list would be a CLAIM about
what a step does, while the stream is the step's own account of what it did.

    scripts/tf-stream.sh   runs terraform and captures the stream
    this script            folds every captured stream into one timeline file
    publish-status.sh      publishes it, under the narrow publish role

Two outputs, and the second one is not optional. `-json` REPLACES the
human-readable apply log in the Actions UI, so losing that to gain a picture
would be a bad trade: this script prints a legible summary — including every
diagnostic in full — to stdout, and writes the machine-readable timeline to
--out.

WHAT MAKES A TIMELINE COMPLETE
------------------------------
Three independent signals, and the weakest one wins. This is the whole point of
the file: a run that dies mid-apply must publish a timeline marked INCOMPLETE,
never a plausible complete one.

    the .rc file      written by tf-stream.sh AFTER terraform returns. Missing
                      means the process never returned - cancelled, killed,
                      runner lost - and no amount of plausible-looking events
                      can outweigh that
    the exit code     non-zero means terraform reported a failure
    the terminal      `change_summary` with operation "apply" or "destroy".
    change_summary    The "plan" one does not count; a stream that stops after
                      it is a stream that stopped in the middle

A resource is complete only if its `apply_start` was answered by an
`apply_complete`. An `apply_start` with no answer is exactly what a killed
apply leaves behind, and it is recorded as incomplete with whatever
`apply_progress` last said about it.

WHAT IS NOT DONE HERE
---------------------
No AWS call is made, and no identifier is enriched into another (ADR-0039 D2).
The page shows `id_value` when `apply_complete` carries one and shows nothing
when it does not.

Usage:
    scripts/fold-timeline.py --environment stage --stream-dir /tmp/tf-streams \
        --out /tmp/timeline-stage.json

Exit status is 0 whenever the fold itself succeeded, INCLUDING for a timeline
marked incomplete or errored. Folding is reporting, not judging: the workflow
step that ran terraform has already failed the build if terraform failed, and a
fold that also failed would hide the timeline of the very run that needed one.
It exits non-zero only when it cannot do its own job — an unreadable stream
directory, an unwritable --out.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "timeline/1"

# The event types this script understands. Anything else is counted and
# ignored rather than guessed at: the set is Terraform's, it is
# version-dependent, and a fold that crashed on an unfamiliar line would take
# the log down with it.
KNOWN_TYPES = {
    "version",
    "log",
    "planned_change",
    "change_summary",
    "outputs",
    "refresh_start",
    "refresh_complete",
    "apply_start",
    "apply_progress",
    "apply_complete",
    "apply_errored",
    "provision_start",
    "provision_progress",
    "provision_complete",
    "provision_errored",
    "diagnostic",
    "resource_drift",
    "test_abstract",
}

TERMINAL_OPERATIONS = {"apply", "destroy"}


def parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def seconds_between(start: datetime | None, end: datetime | None) -> float | None:
    if start is None or end is None:
        return None
    return round((end - start).total_seconds(), 3)


class Operation:
    """One terraform invocation, folded from one captured stream."""

    def __init__(self, order: int, label: str, stream_path: Path):
        self.order = order
        self.label = label
        self.stream_path = stream_path
        self.exit_code: int | None = None
        self.tool: dict | None = None
        self.argv: str | None = None
        self.invoked: str | None = None
        self.command: str | None = None
        self.counts: dict | None = None
        self.saw_terminal_summary = False
        self.resources: dict[str, dict] = {}
        self.order_seen: list[str] = []
        self.diagnostics: list[dict] = []
        self.event_types: dict[str, int] = {}
        self.unparsed_lines = 0
        self.unknown_types: dict[str, int] = {}
        self.first_ts: datetime | None = None
        self.last_ts: datetime | None = None

    # -- reading ---------------------------------------------------------
    def read(self) -> None:
        # What was RUN. The stream cannot say: an apply killed before its
        # terminal summary leaves only the "plan" change_summary behind, and a
        # fold reading the stream alone would label a half-finished apply a
        # plan. tf-stream.sh writes this before terraform starts.
        cmd_path = self.stream_path.with_suffix(".cmd")
        if cmd_path.exists():
            self.argv = cmd_path.read_text().strip() or None
            if self.argv:
                self.invoked = self.argv.split()[0]

        rc_path = self.stream_path.with_suffix(".rc")
        if rc_path.exists():
            text = rc_path.read_text().strip()
            try:
                self.exit_code = int(text)
            except ValueError:
                # A .rc that exists but says something unreadable is not a
                # missing .rc: the process DID return, we just cannot say
                # with what. Recorded as a diagnostic rather than discarded.
                self.exit_code = None
                self.diagnostics.append(
                    {
                        "severity": "error",
                        "summary": "unreadable exit code",
                        "detail": f"{rc_path.name} contains {text!r}",
                        "address": None,
                    }
                )

        with self.stream_path.open("r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    # Terraform writes one JSON object per line, but a killed
                    # process can leave a half-written last line, and anything
                    # a wrapper prints onto the same stream lands here too.
                    self.unparsed_lines += 1
                    continue
                if not isinstance(event, dict):
                    self.unparsed_lines += 1
                    continue
                self.consume(event)

    def consume(self, event: dict) -> None:
        etype = event.get("type", "<none>")
        self.event_types[etype] = self.event_types.get(etype, 0) + 1
        if etype not in KNOWN_TYPES:
            self.unknown_types[etype] = self.unknown_types.get(etype, 0) + 1

        ts = parse_ts(event.get("@timestamp"))
        if ts is not None:
            if self.first_ts is None or ts < self.first_ts:
                self.first_ts = ts
            if self.last_ts is None or ts > self.last_ts:
                self.last_ts = ts

        if etype == "version":
            # Terraform reports {"terraform": "1.x.y"}; OpenTofu reports
            # {"tofu": "1.x.y"}. Neither name is assumed.
            name, version = None, None
            for key in ("terraform", "tofu"):
                if key in event:
                    name, version = key, event[key]
                    break
            self.tool = {"name": name, "version": version, "message": event.get("@message")}
            return

        if etype == "change_summary":
            changes = event.get("changes") or {}
            operation = changes.get("operation")
            if operation in TERMINAL_OPERATIONS:
                self.saw_terminal_summary = True
                self.command = operation
                self.counts = {
                    "add": changes.get("add"),
                    "change": changes.get("change"),
                    "remove": changes.get("remove"),
                    "import": changes.get("import"),
                }
            elif operation == "plan" and self.command is None:
                # Records what this invocation was going to do, for a stream
                # that never reached its terminal summary.
                self.command = "plan"
            return

        if etype == "diagnostic":
            diag = event.get("diagnostic") or {}
            self.diagnostics.append(
                {
                    "severity": diag.get("severity"),
                    "summary": diag.get("summary"),
                    "detail": diag.get("detail"),
                    "address": diag.get("address"),
                }
            )
            return

        if etype in ("apply_start", "apply_progress", "apply_complete", "apply_errored"):
            self.consume_hook(etype, event, ts)
            return

    def consume_hook(self, etype: str, event: dict, ts: datetime | None) -> None:
        hook = event.get("hook") or {}
        resource = hook.get("resource") or {}
        address = resource.get("addr")
        if not address:
            return
        record = self.resources.get(address)
        if record is None:
            record = {
                "address": address,
                "module": resource.get("module") or "",
                "type": resource.get("resource_type"),
                "name": resource.get("resource_name"),
                "action": hook.get("action"),
                "status": "incomplete",
                "started_at": None,
                "finished_at": None,
                "elapsed_seconds": None,
                "last_progress_seconds": None,
                "id_key": None,
                "id_value": None,
            }
            self.resources[address] = record
            self.order_seen.append(address)

        if hook.get("action"):
            record["action"] = hook.get("action")

        if etype == "apply_start":
            record["started_at"] = iso(ts)
        elif etype == "apply_progress":
            record["last_progress_seconds"] = hook.get("elapsed_seconds")
        elif etype == "apply_complete":
            record["status"] = "complete"
            record["finished_at"] = iso(ts)
            record["elapsed_seconds"] = hook.get("elapsed_seconds")
            record["id_key"] = hook.get("id_key")
            record["id_value"] = hook.get("id_value")
        elif etype == "apply_errored":
            record["status"] = "errored"
            record["finished_at"] = iso(ts)
            record["elapsed_seconds"] = hook.get("elapsed_seconds")

    # -- verdict ---------------------------------------------------------
    @property
    def status(self) -> str:
        if self.exit_code is None:
            # No .rc: terraform never returned. Nothing else can outweigh it.
            return "incomplete"
        if any(r["status"] == "errored" for r in self.resources.values()):
            return "errored"
        if self.exit_code != 0:
            return "errored"
        if not self.saw_terminal_summary:
            return "incomplete"
        if any(r["status"] != "complete" for r in self.resources.values()):
            return "incomplete"
        return "complete"

    @property
    def reason(self) -> str | None:
        if self.exit_code is None:
            return "terraform did not return: no exit code was recorded"
        if any(r["status"] == "errored" for r in self.resources.values()):
            return "at least one resource errored"
        if self.exit_code != 0:
            return f"terraform exited {self.exit_code}"
        if not self.saw_terminal_summary:
            return "the stream has no terminal change_summary"
        if any(r["status"] != "complete" for r in self.resources.values()):
            return "a resource started and was never completed"
        return None

    def to_json(self) -> dict:
        resources = [self.resources[addr] for addr in self.order_seen]
        return {
            "order": self.order,
            "label": self.label,
            # What was run beats what the stream got as far as saying.
            "command": self.invoked or self.command,
            "reached": self.command,
            "argv": self.argv,
            "status": self.status,
            "reason": self.reason,
            "exit_code": self.exit_code,
            "started_at": iso(self.first_ts),
            "finished_at": iso(self.last_ts),
            "duration_seconds": seconds_between(self.first_ts, self.last_ts),
            "counts": self.counts,
            "resources": resources,
            "diagnostics": self.diagnostics,
            "stream": {
                "file": self.stream_path.name,
                "events": sum(self.event_types.values()),
                "unparsed_lines": self.unparsed_lines,
                "unknown_types": self.unknown_types,
                "event_types": dict(sorted(self.event_types.items())),
            },
        }


def collect_streams(stream_dir: Path) -> list[Operation]:
    """Every *.jsonl in the directory, in filename order.

    The filename carries the order and the label: `01-apply.jsonl`. Presence is
    itself a fact — tf-stream.sh creates the file before terraform starts, so a
    step that began and was killed leaves a stream with no .rc beside it, which
    is precisely the case this whole file exists to report honestly.
    """
    operations: list[Operation] = []
    for index, path in enumerate(sorted(stream_dir.glob("*.jsonl")), start=1):
        stem = path.stem
        label = stem.split("-", 1)[1] if "-" in stem and stem.split("-", 1)[0].isdigit() else stem
        operations.append(Operation(index, label, path))
    return operations


def timeline_status(operations: list[Operation]) -> str:
    statuses = [op.status for op in operations]
    if not statuses:
        return "incomplete"
    if "incomplete" in statuses:
        return "incomplete"
    if "errored" in statuses:
        return "errored"
    return "complete"


def build(environment: str, operations: list[Operation], run: dict) -> dict:
    folded = [op.to_json() for op in operations]
    starts = [parse_ts(op["started_at"]) for op in folded if op["started_at"]]
    ends = [parse_ts(op["finished_at"]) for op in folded if op["finished_at"]]
    tool = next((op.tool for op in operations if op.tool), None)

    created = destroyed = 0
    for op in folded:
        for resource in op["resources"]:
            if resource["status"] != "complete":
                continue
            if resource["action"] in ("create", "replace"):
                created += 1
            elif resource["action"] == "delete":
                destroyed += 1

    return {
        "schema": SCHEMA,
        "environment": environment,
        "status": timeline_status(operations),
        "written_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tool": tool,
        "run": run,
        "started_at": iso(min(starts)) if starts else None,
        "finished_at": iso(max(ends)) if ends else None,
        "duration_seconds": seconds_between(min(starts), max(ends)) if starts and ends else None,
        "totals": {
            "operations": len(folded),
            "resources_observed": sum(len(op["resources"]) for op in folded),
            "resources_created": created,
            "resources_destroyed": destroyed,
        },
        "operations": folded,
    }


# -- the readable log ------------------------------------------------------
# Not decoration. `-json` removes terraform's own human-readable output from
# the Actions UI, so this is the only place a person reads what the apply did.


def render(timeline: dict, out=None) -> None:
    # Resolved at CALL time, not at definition time. A default of `sys.stdout`
    # binds the stream this module was imported with, which quietly ignores any
    # later redirection - and the first thing to notice was the gate that
    # renders into a buffer to check what the log says.
    sink = sys.stdout if out is None else out

    def line(text: str = "") -> None:
        print(text, file=sink)

    line(f"timeline: {timeline['environment']} — {timeline['status'].upper()}")
    tool = timeline.get("tool") or {}
    if tool.get("version"):
        line(f"tool:     {tool.get('name')} {tool.get('version')}")
    if timeline.get("duration_seconds") is not None:
        line(f"window:   {timeline['started_at']} → {timeline['finished_at']} "
             f"({timeline['duration_seconds']:.0f}s)")
    totals = timeline["totals"]
    line(f"totals:   {totals['operations']} operation(s), "
         f"{totals['resources_created']} created, {totals['resources_destroyed']} destroyed")
    line()

    for op in timeline["operations"]:
        header = f"[{op['order']}] {op['label']} ({op['command'] or 'unknown'}) — {op['status'].upper()}"
        line(f"::group::{header}")
        if op["reason"]:
            line(f"    why: {op['reason']}")
        line(f"    exit code: {op['exit_code'] if op['exit_code'] is not None else '<none recorded>'}")
        if op["counts"]:
            counts = op["counts"]
            line(f"    summary:   add {counts['add']}, change {counts['change']}, "
                 f"remove {counts['remove']}")
        stream = op["stream"]
        line(f"    stream:    {stream['file']}, {stream['events']} events")
        if stream["unparsed_lines"]:
            line(f"    UNPARSED:  {stream['unparsed_lines']} line(s) were not JSON")
        if stream["unknown_types"]:
            line(f"    UNKNOWN:   event types this fold does not model: "
                 f"{', '.join(sorted(stream['unknown_types']))}")
        line()

        if op["resources"]:
            width = max(len(r["address"]) for r in op["resources"])
            width = min(width, 60)
            line(f"    {'resource'.ljust(width)}  {'action':<8} {'secs':>5}  {'status':<10} id")
            for r in op["resources"]:
                secs = r["elapsed_seconds"]
                if secs is None:
                    secs = r["last_progress_seconds"]
                    secs_text = f"{secs}+" if secs is not None else "-"
                else:
                    secs_text = str(secs)
                identity = r["id_value"] or ""
                if len(identity) > 60:
                    identity = identity[:57] + "..."
                line(f"    {r['address'][:width].ljust(width)}  {str(r['action'] or '-'):<8} "
                     f"{secs_text:>5}  {r['status']:<10} {identity}")
        else:
            line("    no resource events in this stream")
        line("::endgroup::")

        # Diagnostics are printed OUTSIDE the collapsed group and in full.
        # A collapsed error is a lost error, and the whole cost of -json is
        # paid right here.
        errors = [d for d in op["diagnostics"] if d["severity"] == "error"]
        warnings = [d for d in op["diagnostics"] if d["severity"] != "error"]
        for diag in errors:
            line(f"ERROR   [{op['label']}] {diag['summary']}"
                 + (f"  ({diag['address']})" if diag["address"] else ""))
            if diag["detail"]:
                for detail_line in str(diag["detail"]).rstrip().splitlines():
                    line(f"        {detail_line}")
        for diag in warnings:
            line(f"warning [{op['label']}] {diag['summary']}"
                 + (f"  ({diag['address']})" if diag["address"] else ""))
        if errors or warnings:
            line()


def github_run() -> dict:
    return {
        "id": os.environ.get("GITHUB_RUN_ID") or "local",
        "number": os.environ.get("GITHUB_RUN_NUMBER") or None,
        "attempt": os.environ.get("GITHUB_RUN_ATTEMPT") or None,
        "workflow": os.environ.get("GITHUB_WORKFLOW") or None,
        "url": (
            f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/"
            f"{os.environ.get('GITHUB_REPOSITORY', 'UVE-QA/aws-devops-sdet-demo')}/actions/runs/"
            f"{os.environ.get('GITHUB_RUN_ID', 'local')}"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--environment", required=True)
    parser.add_argument("--stream-dir", required=True, type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="write --out without printing the readable summary",
    )
    args = parser.parse_args(argv)

    if not args.stream_dir.is_dir():
        # Not an error. A workflow can fail before terraform ever runs, and a
        # timeline asserting anything about that run would be an invention.
        print(f"no stream directory at {args.stream_dir}: no timeline written")
        return 0

    operations = collect_streams(args.stream_dir)
    if not operations:
        print(f"no *.jsonl streams in {args.stream_dir}: no timeline written")
        return 0

    for op in operations:
        op.read()

    timeline = build(args.environment, operations, github_run())

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(timeline, indent=2) + "\n", encoding="utf-8")

    if not args.quiet:
        render(timeline)
        if args.out:
            print(f"timeline written to {args.out}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
