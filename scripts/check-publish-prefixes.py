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
WRITER = ROOT / "scripts/publish-status.sh"
SYNCER = ROOT / "scripts/publish-site.sh"

# `s3://${SITE_BUCKET}/<prefix>/...` - the first path segment is the prefix, and
# a destination with no segment at all (the bucket root) would be a different
# and much louder problem.
WRITES = re.compile(r"s3://\$\{SITE_BUCKET\}/([A-Za-z0-9_-]+)/")
EXCLUDES = re.compile(r"--exclude\s+\"([A-Za-z0-9_-]+)/\*\"")


def main() -> int:
    for path in (WRITER, SYNCER):
        if not path.is_file():
            print(f"publish-prefixes: REFUSED\n{path.relative_to(ROOT)} does not exist")
            return 1

    written = sorted(set(WRITES.findall(WRITER.read_text())))
    syncer = SYNCER.read_text()
    excluded = set(EXCLUDES.findall(syncer))

    if not written:
        # The empty result that reads as clean. A regex that stopped matching
        # would otherwise report every prefix as covered, which is the state
        # this whole check exists to make impossible.
        print(
            "publish-prefixes: REFUSED\n"
            f"no s3://${{SITE_BUCKET}}/<prefix>/ destination found in "
            f"{WRITER.relative_to(ROOT)}. A check that found nothing to check is not a "
            "green check."
        )
        return 1
    if "--delete" not in syncer:
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
                f"  {WRITER.name} writes s3://<bucket>/{p}/ and {SYNCER.name} does not "
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
