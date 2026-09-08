#!/usr/bin/env python3
"""Every prefix the lifecycle writes is excluded from the site sync (ADR-0044).

Two scripts share one bucket and they are not peers:

    scripts/publish-status.sh   writes what a RUN observed - status, reports,
                                timeline, results. Runs on every cycle.
    scripts/publish-site.sh     `aws s3 sync site/ --delete`. Runs on every push
                                to main that touches site/.

`--delete` means the second removes anything the first wrote and the repository
does not contain, unless the prefix is named in an `--exclude`. That list is
therefore a piece of one script that only makes sense in terms of the other, and
keeping it correct was a rule written in a comment:

    "ONE PREFIX PER THING THE LIFECYCLE WRITES, and adding a prefix means adding
     a line here in the same commit."

On 2026-08-08 the rule was broken exactly as its own comment predicted. ADR-0042
had added `results/` to publish-status.sh eight days after that comment was
written; nothing added the matching `--exclude`; and because no push to main
touched site/ in between, the two scripts never ran in the wrong order. The next
push that did - the one publishing the page that reads those results - deleted
every one of them. The bucket has no versioning. They are gone.

So the correspondence is read out of both files instead of being remembered:

    scripts/check-publish-prefixes.py

Exit status: 0 if every written prefix is excluded, 1 otherwise. Reads two files,
calls nothing, costs nothing.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SYNCER = ROOT / "scripts/publish-site.sh"

# EVERY PUBLISHER, FOUND RATHER THAN NAMED. This was `publish-status.sh` alone,
# which was true when it was written and is the same shape as the defect this
# whole check exists for: a rule that holds until somebody adds a second thing
# and does not remember the line. Phase 39 added scripts/publish-progress.sh,
# and a checker naming one file would have been green over it.
#
# `publish-*.sh` minus the syncer, because the syncer is the OTHER side of the
# correspondence and reading it as a writer would make it exclude itself.
def writers() -> list[pathlib.Path]:
    return sorted(
        p for p in (ROOT / "scripts").glob("publish-*.sh") if p != SYNCER
    )

# `s3://${SITE_BUCKET}/<prefix>/...` - the first path segment is the prefix, and
# a destination with no segment at all (the bucket root) would be a different
# and much louder problem.
WRITES = re.compile(r"s3://\$\{SITE_BUCKET\}/([A-Za-z0-9_-]+)/")
EXCLUDES = re.compile(r"--exclude\s+\"([A-Za-z0-9_-]+)/\*\"")


def main() -> int:
    found = writers()
    if not found:
        print("publish-prefixes: REFUSED\nno scripts/publish-*.sh writer was found at all")
        return 1
    for path in found + [SYNCER]:
        if not path.is_file():
            print(f"publish-prefixes: REFUSED\n{path.relative_to(ROOT)} does not exist")
            return 1

    written = sorted({
        prefix
        for path in found
        for prefix in WRITES.findall(path.read_text())
    })
    syncer = SYNCER.read_text()
    excluded = set(EXCLUDES.findall(syncer))

    if not written:
        # The empty result that reads as clean. A regex that stopped matching
        # would otherwise report every prefix as covered, which is the state
        # this whole check exists to make impossible.
        print(
            "publish-prefixes: REFUSED\n"
            f"no s3://${{SITE_BUCKET}}/<prefix>/ destination found in any of "
            + ", ".join(str(p.relative_to(ROOT)) for p in found)
            + ". A check that found nothing to check is not a green check."
        )
        return 1
    # As an ARGUMENT, not as a substring. `"--delete" in syncer` was the first
    # version and it could not fail: the file's own comment explains what
    # `aws s3 sync --delete` does, so the string is present whatever the command
    # does. The break test refused to break, which is how that was found - the
    # check was testing an assumption about the file rather than the file.
    deleting = any(
        re.match(r"\s*--delete\b", line)
        for line in syncer.splitlines()
        if not line.lstrip().startswith("#")
    )
    if not deleting:
        # If the sync stops deleting, this check is meaningless rather than
        # green - and someone should be told which of the two it is.
        print(
            "publish-prefixes: REFUSED\n"
            f"{SYNCER.relative_to(ROOT)} no longer passes --delete. Either the danger "
            "this check guards is gone, in which case delete the check, or the sync "
            "was rewritten and it needs rereading."
        )
        return 1

    missing = [p for p in written if p not in excluded]
    if missing:
        print("publish-prefixes: MISSING EXCLUSION")
        for p in missing:
            print(
                f"  a publisher writes s3://<bucket>/{p}/ and {SYNCER.name} does not "
                f'exclude it: add --exclude "{p}/*"'
            )
        print(
            "\nThe next push to main that touches site/ will delete everything under "
            "those prefixes. On 2026-08-08 that was results/, and the bucket has no "
            "versioning."
        )
        return 1

    stale = sorted(excluded - set(written))
    if stale:
        # Not a failure: an exclusion for a prefix nothing writes any more is
        # harmless. It is worth SAYING, because the list is meant to be read as
        # the inventory of what the lifecycle publishes.
        print(f"note: {SYNCER.name} excludes {', '.join(stale)}, which nothing writes now")

    print(f"publish-prefixes: {len(written)} written, all excluded - {', '.join(written)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
