#!/usr/bin/env python3
"""Fold the AWS Architecture Icons into one inline SVG sprite, and build the map page.

Why a sprite rather than 17 objects in the bucket: the public page has been one
self-contained file with no build step and no runtime dependency since 11.1c, and
one request per icon to render a picture is a worse trade than the inline
markup, which is a few tens of KB and roughly a quarter of that over the wire,
gzipped by CloudFront. The exact size is PRINTED by this script when it runs
rather than written here, because a number in a comment goes stale the first
time an icon is added - which it just did.

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

    python3 scripts/build-icon-sprite.py     # -> site/map-pilot.html
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ICONS = ROOT / "assets/aws-icons"
TEMPLATE = ROOT / "assets/map-pilot.template.html"
OUT = ROOT / "site/map-pilot.html"
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


def main() -> int:
    template = TEMPLATE.read_text()
    if MARKER not in template:
        print(f"{TEMPLATE} no longer contains {MARKER}; nothing to inject into")
        return 1

    sprite = "\n".join(
        ['<svg xmlns="http://www.w3.org/2000/svg" style="display:none" aria-hidden="true">']
        + [symbol(k) for k in KEYS]
        + ["</svg>"]
    )
    OUT.write_text(template.replace(MARKER, sprite))
    print(f"{OUT.relative_to(ROOT)}: {len(KEYS)} icons, {len(sprite)} bytes of sprite")
    return 0


if __name__ == "__main__":
    sys.exit(main())
