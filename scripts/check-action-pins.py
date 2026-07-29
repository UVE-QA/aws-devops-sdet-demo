#!/usr/bin/env python3
"""Every third-party action must be pinned to a commit SHA, with its version.

A tag is a mutable pointer. `actions/checkout@v7` runs whatever the v7 tag
points at today, and in this repository several jobs hold `id-token: write` and
assume an AWS role - so the code behind that tag is inside the trust boundary
that the whole "no static credentials" story rests on. A commit SHA is
immutable, which is the only property that matters here.

Pinning without a check decays on the first step somebody adds, so this is
mechanical:

  <owner>/<repo>@<40 hex> # <version>

The trailing comment is required, not decorative. Dependabot writes and
maintains it, and without it nobody reading the file can tell whether a pin is
one release old or three years old.

Refuses if it finds no `uses:` at all - a checker that silently scans nothing
passes everything, which is the failure mode this repository keeps meeting.
"""
import glob
import re
import sys

USES = re.compile(r"^\s*uses:\s*(?P<ref>\S+)\s*(?:#\s*(?P<comment>.*))?$")
PINNED = re.compile(r"^[^@\s]+/[^@\s]+@[0-9a-f]{40}$")
VERSION_COMMENT = re.compile(r"^v?\d")


def main() -> int:
    problems: list[str] = []
    seen = 0

    for path in sorted(glob.glob(".github/workflows/*.yml")):
        for number, line in enumerate(open(path), start=1):
            match = USES.match(line.rstrip("\n"))
            if not match:
                continue
            seen += 1
            ref = match.group("ref")
            comment = (match.group("comment") or "").strip()

            # A local action lives in this repository and moves with it.
            if ref.startswith("./"):
                continue
            if not PINNED.match(ref):
                problems.append(
                    f"{path}:{number}: not pinned to a commit SHA -> {ref}"
                )
                continue
            if not VERSION_COMMENT.match(comment):
                problems.append(
                    f"{path}:{number}: pinned, but no version comment -> {ref}"
                )

    if seen == 0:
        print(
            "action-pins: found no `uses:` lines in .github/workflows/ at all. "
            "Either the workflows moved or the pattern is broken. Refusing to "
            "pass without checking anything."
        )
        return 1

    if problems:
        print(f"action-pins: {seen} action references, {len(problems)} unpinned:")
        for problem in problems:
            print(f"  {problem}")
        print(
            "\nPin it: uses: owner/repo@<40-hex commit sha> # vX.Y.Z\n"
            "Resolve the sha without trusting a web page:\n"
            "  git ls-remote https://github.com/owner/repo refs/tags/vX.Y.Z^{}"
        )
        return 1

    print(f"action-pins: {seen} action references, all pinned to a commit SHA")
    return 0


if __name__ == "__main__":
    sys.exit(main())
