#!/usr/bin/env python3
"""Build site/index.html: the icons folded into one inline sprite, injected into the template.

Why a sprite rather than one bucket object per icon: the PUBLISHED page has been
a single self-contained file with no runtime dependency since 11.1c, and one
request per icon to render a picture is a worse trade than the inline markup,
which is a few tens of KB and roughly a quarter of that over the wire, gzipped
by CloudFront. The exact size is PRINTED by this script when it runs rather than
written here, because a number in a comment goes stale the first time an icon is
added - which it has now done twice, and the second time it was this sentence
saying "17 objects" over a list of eighteen. The count is not written here
either; it is len(KEYS), a few lines below.

What 20a DID change is "no build step". There is one now, it is this script, and
its output is committed - which is why `--check` exists.

The icons are used UNMODIFIED. No recolouring, no reproportioning, no cropping —
AWS's trademark guidelines prohibit altering the marks, and this script is the
one place that could have done it, so it says so here. The only rewriting is to
namespace each icon's internal element ids: a directory of files that each call
an element "Rectangle" cannot share one DOM without colliding. Geometry, colour and
viewBox are untouched.

Provenance and the licence position are in assets/aws-icons/NOTICE.md.

The inputs live OUTSIDE site/ on purpose: publish-site.yml fires on any push to
site/** and syncs the whole directory to the public bucket, so a build input left
there would be published too - and the template, served without its sprite, would
render a map with no icons. A page that quietly says something untrue is the
defect this whole phase exists to remove.

    python3 scripts/build-site-page.py           # -> site/index.html
    python3 scripts/build-site-page.py --check   # the drift gate; writes nothing
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ICONS = ROOT / "assets/aws-icons"
TEMPLATE = ROOT / "assets/index.template.html"
OUT = ROOT / "site/index.html"
MARKER = "<!--ICON-SPRITE-->"

# The service keys the page asks for, by <use href="#ic-KEY">. A key here with no
# file is an error rather than a silently empty box.
KEYS = [
    "s3", "iam", "secretsmanager", "acm", "ecr", "ecs", "route53", "cloudfront",
    "vpc", "elb", "rds", "dynamodb", "cloudwatch", "budgets", "lambda", "sns",
    "eventbridge", "lightsail",
]


def symbol(key: str) -> str:
    path = ICONS / f"{key}.svg"
    if not path.is_file():
        raise SystemExit(f"missing icon: {path}")
    raw = path.read_text()

    vb = re.search(r'viewBox="([^"]+)"', raw)
    if not vb:
        raise SystemExit(f"{path} has no viewBox; refusing to guess one")

    inner = raw.split(">", 2)[2].rsplit("</svg>", 1)[0]
    inner = re.sub(r"<title>.*?</title>", "", inner, flags=re.S)

    for i in sorted(set(re.findall(r'\sid="([^"]+)"', inner)), key=len, reverse=True):
        esc = re.escape(i)
        inner = re.sub(rf'(\sid=")({esc})(")', rf"\g<1>{key}-{i}\g<3>", inner)
        inner = re.sub(rf"(url\(#){esc}(\))", rf"\g<1>{key}-{i}\g<2>", inner)
        inner = re.sub(rf'((?:xlink:)?href="#){esc}(")', rf"\g<1>{key}-{i}\g<2>", inner)

    return f'<symbol id="ic-{key}" viewBox="{vb.group(1)}">{inner.strip()}</symbol>'


def build() -> str:
    template = TEMPLATE.read_text()
    if MARKER not in template:
        raise SystemExit(f"{TEMPLATE} no longer contains {MARKER}; nothing to inject into")

    sprite = "\n".join(
        ['<svg xmlns="http://www.w3.org/2000/svg" style="display:none" aria-hidden="true">']
        + [symbol(k) for k in KEYS]
        + ["</svg>"]
    )
    print(f"{len(KEYS)} icons, {len(sprite.encode()):,} bytes of sprite", file=sys.stderr)
    return template.replace(MARKER, sprite)


def main(argv: list[str]) -> int:
    page = build()

    # --check is the drift gate. site/index.html is a BUILD OUTPUT that is
    # committed, and a committed output invites being edited in place: the edit
    # then survives until the next build silently reverts it, which is a slower
    # and quieter version of the defect this phase exists to remove. So the
    # committed page must be byte-identical to a fresh build, and CI says so.
    if "--check" in argv:
        if not OUT.is_file():
            print(f"site-page-check: {OUT.relative_to(ROOT)} does not exist. Run `make site-page`.")
            return 1
        if OUT.read_text() != page:
            print(
                f"site-page-check: {OUT.relative_to(ROOT)} is not what the template builds.\n"
                "  Edit assets/index.template.html, not the built page, then run `make site-page`."
            )
            return 1
        print(f"site-page-check: {OUT.relative_to(ROOT)} matches the template")
        return 0

    OUT.write_text(page)
    print(f"{OUT.relative_to(ROOT)}: {len(page.encode()):,} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
