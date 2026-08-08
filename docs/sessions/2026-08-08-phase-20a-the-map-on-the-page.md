# 2026-08-08 — Phase 20a closed: the map on the page

The last piece of 20a, and two fixes to the session machinery that this day
earned twice over.

## What this session established

The hand-written "What happens, in the order it happens" section is gone from
`site/index.html`. In its place the front page renders `site/data/topology.json`
— the same generated file the pilot rendered, the one gated by `make
site-data-check` — as the band above the cycle, the permanent levels, the
serpentine of phases, the cut that names every resource, and the counts. Nothing
on that part of the page is written by hand any more, which was the whole point:
the section it replaced was the one telling every visitor there were five
permanent state levels while standing on the sixth.

**The page became a build output, which was not in the plan.** The map needs the
icon sprite inline — 18 icons, 50,168 bytes, the position on AWS's terms is in
`assets/aws-icons/NOTICE.md` — and a page that fetches a sprite is a page with a
runtime dependency. So `assets/index.template.html` is now the source,
`scripts/build-site-page.py` builds `site/index.html`, and `make site-page` is
the target. The template lives outside `site/` for the reason the pilot's did:
`publish-site` syncs the whole directory to the public bucket, and a template
served without its sprite renders a map with no icons.

That buys a new way to be wrong. A committed build output invites being edited
in place, and the edit survives exactly until the next build silently reverts
it — slower and quieter than the defect this phase exists to remove, and the
same shape. So `make site-page-check` requires the committed page to be
byte-identical to a fresh build, and it runs in `ci.yml`.

**The pilot is retired** — `site/map-pilot.html`, its template and its target.
`publish-site.sh` syncs with `--delete`, so the published copy went with the
commit. Keeping it would have left two renderings of one file maintained
separately, which is precisely the shape being removed.

## Two layout defects, both invisible to the check that was watching

The pilot measured `scrollWidth == clientWidth` at 1440 / 1180 / 834 / 390 and
was green at all four. It was measuring the DOCUMENT, and a box that overflows
its own parent never reaches the document. Measuring each box against ITS OWN
container found two:

```text
packer      a row renders phase | gap | arrow | gap | phase - two gaps per
            join. The greedy serpentine packer charged itself one. At 1180 the
            first row came out 1132px inside a 1125px box. At 1440 there was
            slack and nothing showed
.node .head up to 22px wider than its own node, at every width. Recorded and
            left by the generator session on the grounds that layout here is
            decided by looking, which was right - this is the session that
            looked
```

The head took three attempts and the two failures are the useful part.
`overflow-wrap: anywhere` stopped the overflow and rendered `Applicati on Load
Balancer`, `RDS PostgreS QL`, `CloudWa tch` — a fix whose damage is only visible
in a screenshot, exactly like the `undefineds` the generator session found.
`flex-wrap: wrap` stopped the mid-word breaks and dropped the icon onto a line
of its own, away from the name it belongs to. What was actually stealing the
width was the environment tag, which is redundant with the phase header — it
already says `stage` or `prod` — and which is kept anyway, because 20c gives a
suite an identity of suite × environment. The head is now a two-row grid: icon
and name on one line, tag beneath, the same on every node at every width.

Re-rendered through Playwright at 1440 / 1180 / 834 / 390, cut shut and cut
open: no row overflows its container, no head overflows its node, the document
fits, and nothing prints `undefined`.

## The gate, broken on purpose

Six paths, five red, both controls green, exit codes written to a FILE with the
tree committed first. Evidence:
`docs/sessions/2026-08-08-phase-20a-page-break-tests.log`.

```text
1  the built page edited by hand
2  the built page deleted
3  the TEMPLATE edited and the page not rebuilt - the drift the gate exists for
4  the template loses its injection marker
5  an icon the page asks for is missing
0/6  controls: the untouched tree, before and after
```

One claim in that log was written before it was checked — that the script itself
exits 1 where `make` reports 2 — and the first attempt to check it ran against a
CLEAN tree and returned 0, which proves nothing. Re-run against a broken one it
returns 1. A control that cannot fail is not a control, in miniature.

## Three stale numbers, again

All three found on the way past, and all three the species this phase keeps
meeting:

```text
"17 objects"    in the sprite builder's docstring, over a list of eighteen. The
                sentence explaining why a number should not be written down
counted as bytes  the builder printed len(str) and called it bytes: 118,577
                against 118,667 on disk, which is what em dashes cost
"no build step" in three documents about site/index.html, true until this commit
```

The count is no longer written anywhere — it is `len(KEYS)` — and the sizes are
measured with `.encode()`.

## The session machinery, fixed at the end

Two small things this day earned:

```text
session-close.sh:32  the summary it prints came from `ls <today>-*.md | tail -1`,
                     which sorts alphabetically. With four summaries dated
                     2026-08-08 it printed the layout pilot while the newest was
                     the generator session. Now taken from the LAST ROW of
                     INDEX.md, whose chronological order this same script
                     already enforces - one ordering, not two
session-close.sh:93  the same assumption again, finding the previous session to
                     locate the base commit for the ADR block. It also counted
                     *.log evidence files as sessions. On the tree it was
                     measured against it landed on the right file BY ACCIDENT;
                     adding this session's own break-test log made the same line
                     return the LOG. Both were run, before and after
session-primer       the WORKING name for a chat was taken from the phase title
                     in the cursor. A sub-phase routinely takes more than one
                     session and the title does not change while it does: 20a
                     took three, 19g took two across midnight, and every one of
                     them would have opened under the same name. Now taken from
                     the cursor's NEXT ALLOWED STEP, which is the line that
                     differs - and which exists because the previous session
                     wrote it
```

## Files

```text
assets/index.template.html          new - the dashboard's source, map merged in
assets/map-pilot.template.html      deleted
site/index.html                     now a build output
site/map-pilot.html                 deleted
scripts/build-site-page.py          renamed from build-icon-sprite.py, --check
Makefile                            site-page, site-page-check; site-pilot gone
.github/workflows/ci.yml            site-page-check
scripts/session-close.sh            both orderings taken from INDEX
docs/session-primer.md              the working-name rule
docs/phase-gates.md                 20a closed; the pilot entry marked retired
docs/next-phases.md                 what the page settled; what is carried past
docs/project-prompt.md              the template is a file now
docs/discussion-log.md              current state
```

## Cost

**$0.** Nothing applied to AWS, no AWS API called, no environment at any point.
The page publishes on push to `site/**`.

## Next allowed step

**20b** — the timeline from Terraform's own `-json` event stream. It needs one
cycle, about $0.03. Until it lands the map renders entirely unobserved, and says
so on the page.

Carried past 20a rather than done in it: `docs/architecture.md` still draws the
same picture by hand, in Mermaid. The public page can no longer disagree with
`infra/`; the repository's own diagram still can, and a reader meets it first.
