#!/usr/bin/env python3
"""The gate list, and the two things you can do with it (Phase 23).

`make gates`        run every gate assets/gates.json marks as runnable in a
                    plain checkout, print a table, and exit non-zero if any of
                    them failed.
`make gates-check`  the refusals over the list itself, run alone.

WHY THIS EXISTS. The exit checklist and CI used to carry SEPARATE lists of the
cheap gates: ci.yml ran twelve, scripts/session-close.sh ran three. A session
could therefore print `session-close: clean` and redden main with the same
commit, and one did twice - 20i and 21, both because topology.json counts the
files in docs/decisions/ and a documents-only session moves a generated number
without going near the generator. Phase 22 closed that particular hole and said
so in a comment: the shape was still two lists that can disagree.

WHAT THE ONE LIST COSTS, AND WHAT PAYS FOR IT. Two lists cannot both shrink by
accident; one can. Deleting a line here weakens BOTH readers at once, silently,
which is a worse failure than the one being fixed. So the list does not stand on
its own: `--check` DISCOVERS the gates that ought to be in it, out of the
Makefile and out of ci.yml, and refuses when one is missing. The discovery holds
no list of its own - it reads the repository - which is the difference between a
second reader and a third copy.

Standard library only, on purpose: this runs as the first thing in a checkout,
before any virtualenv exists, and on a runner where the gates step installs
nothing.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIST = ROOT / "assets" / "gates.json"
MAKEFILE = ROOT / "Makefile"
CI = ROOT / ".github" / "workflows" / "ci.yml"

problems: list[str] = []


def refuse(message: str) -> None:
    problems.append(message)


def load_list() -> dict:
    if not LIST.exists():
        print(f"gates: {LIST.relative_to(ROOT)} is missing, so there is no list "
              f"to run. Refusing to report a pass over nothing.")
        sys.exit(1)
    try:
        return json.loads(LIST.read_text())
    except json.JSONDecodeError as exc:
        print(f"gates: {LIST.relative_to(ROOT)} is not valid JSON ({exc}). Refusing.")
        sys.exit(1)


def makefile_targets() -> dict[str, list[str]]:
    """Every target in the Makefile, with the recipe lines under it.

    A .PHONY line is not the inventory: it is a second list, and it has been
    out of date in this repository before. The target definitions are.
    """
    targets: dict[str, list[str]] = {}
    current: str | None = None
    for line in MAKEFILE.read_text().splitlines():
        if line.startswith("\t"):
            if current:
                targets[current].append(line)
            continue
        match = re.match(r"^([A-Za-z0-9][A-Za-z0-9_.-]*)\s*:(?!=)", line)
        if match and not line.startswith(".PHONY"):
            current = match.group(1)
            targets.setdefault(current, [])
        elif line.strip() == "" or not line.startswith(" "):
            current = None
    return targets


def ci_make_targets() -> set[str]:
    """Targets ci.yml invokes as `make <target>`, comments excluded.

    Comment lines are dropped because ci.yml's comments name make targets while
    discussing them, and a target discussed is not a target run. A `make` call
    inside a multi-line run block IS found: the pattern is not anchored to
    `run:`.
    """
    found: set[str] = set()
    if not CI.exists():
        refuse(f"{CI.relative_to(ROOT)} is missing, so what CI runs cannot be "
               f"discovered. Refusing rather than checking half the question.")
        return found
    for line in CI.read_text().splitlines():
        if line.lstrip().startswith("#"):
            continue
        for name in re.findall(r"(?:^|\s)make\s+([a-z][a-z0-9-]*)", line):
            found.add(name)
    return found


def check(data: dict) -> list[dict]:
    """The refusals. Returns the entries, and appends to `problems`."""
    entries = data.get("gates")
    if not isinstance(entries, list) or not entries:
        refuse("the list is empty or missing - a runner with nothing in it is "
               "green for the wrong reason")
        return []

    runner = data.get("runner")
    checker = data.get("checker")
    if not runner or not checker:
        refuse("the list does not name its own `runner` and `checker` targets, "
               "so discovery cannot tell a gate from the thing that runs gates")

    seen: set[str] = set()
    listed: set[str] = set()
    local: list[str] = []
    for entry in entries:
        name = entry.get("target")
        if not name:
            refuse("an entry has no `target`")
            continue
        if name in seen:
            refuse(f"{name} is listed twice - two entries can disagree")
        seen.add(name)
        listed.add(name)
        if entry.get("local"):
            local.append(name)
        elif not str(entry.get("needs", "")).strip():
            refuse(f"{name} is marked as not runnable here and gives no reason. "
                   f"A gate excluded without a reason is a gate nobody will "
                   f"re-examine")

    if not local:
        refuse("no entry is marked `local`, so `make gates` would run nothing "
               "and say so in green")

    targets = makefile_targets()
    for name in sorted(listed):
        if name not in targets:
            refuse(f"the list names {name}, which the Makefile does not define")

    discovered: set[str] = set()
    for name, recipe in targets.items():
        if name.endswith("-check"):
            discovered.add(name)
        elif any("scripts/check-" in line for line in recipe):
            discovered.add(name)
    discovered |= ci_make_targets()
    discovered -= {runner, checker}

    for name in sorted(discovered - listed):
        refuse(f"{name} is a gate this repository runs and the list does not "
               f"carry it - so only one of the two readers would ever run it, "
               f"which is the shape this file exists to remove")

    return entries


def run(entries: list[dict]) -> int:
    local = [e["target"] for e in entries if e.get("local")]
    skipped = [(e["target"], e.get("needs", "")) for e in entries if not e.get("local")]

    print(f"== {len(local)} gate(s) from assets/gates.json ==")
    width = max(len(name) for name in local)
    failures: list[tuple[str, str]] = []
    for name in local:
        print(f"{name:<{width}} ", end="", flush=True)
        completed = subprocess.run(
            ["make", "--no-print-directory", name],
            cwd=ROOT, capture_output=True, text=True,
        )
        if completed.returncode == 0:
            print("ok")
        else:
            print(f"FAIL (exit {completed.returncode})")
            failures.append((name, completed.stdout + completed.stderr))

    print("")
    print("== not run here, and why ==")
    for name, needs in skipped:
        print(f"{name:<24} {needs}")

    if failures:
        print("")
        for name, output in failures:
            print(f"--- {name}")
            for line in output.rstrip().splitlines():
                print(f"    {line}")
        print("")
        print(f"gates: {len(failures)} of {len(local)} failed. "
              f"CI runs this same list and will say the same thing.")
        return 1

    print("")
    print(f"gates: {len(local)}/{len(local)} green. "
          f"{len(skipped)} gate(s) need more than a checkout - see above.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="run the refusals over the list itself and stop")
    args = parser.parse_args()

    data = load_list()
    entries = check(data)

    if problems:
        print("gates-check: the list does not describe this repository")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    if args.check:
        print(f"gates-check: {len(entries)} entries, "
              f"{sum(1 for e in entries if e.get('local'))} runnable here, "
              f"every discovered gate accounted for")
        return 0

    return run(entries)


if __name__ == "__main__":
    sys.exit(main())
