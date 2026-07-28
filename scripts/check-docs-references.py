#!/usr/bin/env python3
"""Check that the LIVING documents describe things that actually exist.

Three of this project's recurring defects are documentation ones: a command that
is copyable and wrong, a path that was renamed, a file listed as existing
because it was planned. This checks the four kinds of claim that can be checked
mechanically, in the documents a reader is expected to act on:

    make <target>       exists in the Makefile
    a repo path         is a tracked file or a real directory
    GET/POST/... route  appears in app/src/main.py
    <name>.yml          exists in .github/workflows/

Historical documents are deliberately NOT checked. docs/sessions/ and the ADRs
record what was true when they were written, and a renamed module must not turn
them red. The living set is listed below and its existence is asserted, so a
rename cannot silently reduce this check to nothing.
"""
import pathlib
import re
import subprocess
import sys

LIVING = ["README.md", "docs/architecture.md", "docs/demo-script.md"]

ROOT = pathlib.Path(__file__).resolve().parent.parent


def main() -> int:
    missing = [d for d in LIVING if not (ROOT / d).is_file()]
    if missing:
        print(f"the living set names files that do not exist: {missing}")
        print("Refusing to pass having checked nothing.")
        return 1

    tracked = set(
        subprocess.run(
            ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.split()
    )
    dirs = {str(p) for f in tracked for p in pathlib.Path(f).parents}
    targets = set(re.findall(r"^([a-zA-Z0-9_-]+):", (ROOT / "Makefile").read_text(), re.M))
    routes = (ROOT / "app/src/main.py").read_text()
    workflows = {p.name for p in (ROOT / ".github/workflows").iterdir()}

    findings = []
    for doc in LIVING:
        text = (ROOT / doc).read_text()

        for target in re.findall(r"\bmake ([a-z][a-z0-9-]+)", text):
            if target not in targets:
                findings.append(f"{doc}: `make {target}` is not a Makefile target")

        pattern = r"(?<![\w./-])((?:docs|infra|app|tests|scripts|site|\.github)/[\w./-]*)"
        for match in re.finditer(pattern, text):
            # A match that runs straight into a placeholder is not a repo path:
            # `app/app/<task-id>` is a CloudWatch log stream, and truncating it
            # at the angle bracket would report a directory nobody claimed.
            if text[match.end():match.end() + 1] == "<":
                continue
            path = match.group(1).rstrip(".,);:").rstrip("/")
            if path not in tracked and path not in dirs:
                findings.append(f"{doc}: `{path}` is neither a tracked file nor a directory")

        for route in re.findall(r"^\s*(?:GET|POST|PATCH|PUT|DELETE)\s+(/[\w/{}-]*)", text, re.M):
            # The docs write {id}; the handler signature spells it {item_id}.
            if f'"{route.replace("{id}", "{item_id}")}"' not in routes:
                findings.append(f"{doc}: route `{route}` is not declared in app/src/main.py")

        for name in re.findall(r"(?<![\w/-])([\w.-]+\.yml)\b", text):
            if name not in workflows:
                findings.append(f"{doc}: workflow `{name}` does not exist")

    for f in findings:
        print(f)
    print(f"{len(LIVING)} documents checked, {len(findings)} findings")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
