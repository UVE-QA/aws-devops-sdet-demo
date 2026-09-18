#!/usr/bin/env python3
"""lifecycle-list-check: the four lifecycle workflows are named in three places
and the three must agree (ADR-0100 D1, amended 2026-09-18).

    assets/index.template.html        WRITERS - the runs the page draws
    .github/workflows/publish-runs.yml  on.workflow_run.workflows - the runs whose
                                        completion writes the final snapshot
    scripts/publish-runs.sh             lifecycle_workflows - the runs the
                                        snapshot lists

A workflow in one and not the others is a cycle the page cannot see, or a
snapshot that never says `completed`, or a history that never shows it.
Reads three files, calls nothing.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def page() -> set[str]:
    text = (ROOT / "assets/index.template.html").read_text(encoding="utf-8")
    m = re.search(r"var WRITERS = \{(.*?)\n\s*\};", text, re.S)
    if not m:
        raise SystemExit("lifecycle-list-check: no WRITERS table in the page")
    return {p.rsplit("/", 1)[-1] for p in re.findall(r'"\.github/workflows/([^"]+)"', m.group(1))}


def hook() -> set[str]:
    text = (ROOT / ".github/workflows/publish-runs.yml").read_text(encoding="utf-8")
    m = re.search(r"workflows:\s*\[([^\]]*)\]", text)
    if not m:
        raise SystemExit("lifecycle-list-check: publish-runs.yml names no workflows")
    names = {n.strip() for n in m.group(1).split(",") if n.strip()}
    # The trigger names workflows by their `name:`; the files are named the same.
    return {f"{n}.yml" for n in names}


def script() -> set[str]:
    text = (ROOT / "scripts/publish-runs.sh").read_text(encoding="utf-8")
    m = re.search(r'lifecycle_workflows="\$\{LIFECYCLE_WORKFLOWS:-([^}]*)\}"', text)
    if not m:
        raise SystemExit("lifecycle-list-check: publish-runs.sh names no lifecycle workflows")
    return set(m.group(1).split())


def main() -> int:
    copies = {"the page's WRITERS": page(), "publish-runs.yml's trigger": hook(), "publish-runs.sh": script()}
    union = set().union(*copies.values())
    bad = 0
    for name, have in copies.items():
        for wf in sorted(union - have):
            print(f"lifecycle-list-check: {wf} is a lifecycle workflow everywhere but in {name}")
            bad += 1
    for wf in sorted(union):
        if not (ROOT / ".github/workflows" / wf).exists():
            print(f"lifecycle-list-check: {wf} is named as a lifecycle workflow and does not exist")
            bad += 1
    if bad:
        return 1
    print(f"lifecycle-list-check: {len(union)} lifecycle workflows, three copies agree: " + ", ".join(sorted(union)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
