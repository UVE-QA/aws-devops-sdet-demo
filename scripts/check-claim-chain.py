#!/usr/bin/env python3
"""The pipeline's verb chain says the same thing everywhere it is written.

    README.md                     the opening sentence
    assets/index.template.html    the claim paragraph, in `Details`
    assets/index.template.html    the clause beside the name, on the parts row

Three copies of one fact (ADR-0084). They agree today because two were copied
from the third, and nothing checked that they still do - which is the shape this
repository has paid for twice: one definition, two hosts, agreeing right up until
the moment they do not.

WHAT IS COMPARED, AND WHY IT IS NOT THE WHOLE SENTENCE. The three are not meant
to be identical: the README's opening runs on into `and then deletes almost all
of itself`, the page's paragraph into `there is no manual AWS operation...`, and
the row carries one clause because a row is one line. What they MUST share is the
chain of verbs - `deploy -> test -> approve -> promote -> destroy` - because that
chain is the shape of the pipeline, it is what the map below draws as phases, and
a page that names four steps where the map draws five is wrong in the one place a
reader checks first.

Found by writing this: the row clause had dropped `approve`, the only step in the
chain that involves a person, an hour after it was written.

Exit status: 0 if every copy states the same chain, 1 otherwise. Reads two files,
calls nothing, costs nothing.
"""
from __future__ import annotations

import html
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
TEMPLATE = ROOT / "assets/index.template.html"

# A chain is two or more words joined by arrows. Written as `->` in Markdown's
# rendered form, `&rarr;` in the template's source, and U+2192 in both once the
# entities are unescaped - so everything is normalised to one arrow first.
ARROW = re.compile(r"\s*(?:&rarr;|->|→)\s*")
CHAIN = re.compile(r"([a-z]+(?:→[a-z]+)+)")


def chains(text: str) -> list[str]:
    flat = ARROW.sub("→", html.unescape(text))
    flat = re.sub(r"\s+", " ", flat)
    return [c for c in CHAIN.findall(flat.lower())]


def longest(text: str) -> str | None:
    found = chains(text)
    return max(found, key=lambda c: c.count("→")) if found else None


def region(source: str, start: str, end: str, what: str, problems: list[str]) -> str:
    i = source.find(start)
    if i == -1:
        problems.append(f"{what}: could not find {start!r} in {TEMPLATE.name}. "
                        f"The markup moved and this check would have been green over it.")
        return ""
    j = source.find(end, i)
    return source[i : j if j != -1 else i + 2000]


def main() -> int:
    problems: list[str] = []
    for path in (README, TEMPLATE):
        if not path.is_file():
            print(f"claim-chain: REFUSED\n{path.relative_to(ROOT)} does not exist")
            return 1

    source = TEMPLATE.read_text()
    # TWO COPIES NOW, NOT THREE (ADR-0091). The claim paragraph used to open with
    # the chain and the header clause repeated it; the owner asked for the whole
    # opening sentence at the top of the page, on every part, so the paragraph
    # keeps what the chain COSTS to be true and states the chain once, in the
    # header, four lines above wherever that paragraph is read.
    #
    # The check is unchanged in kind and is worth exactly what it was worth: it
    # compares every place the chain IS stated and refuses when one of them
    # cannot be found. Removing a copy removes a way for them to disagree; it
    # does not make the remaining two agree by themselves, which is what ADR-0085
    # exists to notice.
    copies = {
        "README.md opening": longest(README.read_text()[:1200]),
        "the clause in the header": longest(
            region(source, '<span class="ident-what">', "</span>",
                   "the clause in the header", problems)),
    }

    missing = [w for w, c in copies.items() if not c]
    if missing or problems:
        print("claim-chain: REFUSED")
        for p in problems:
            print(f"  - {p}")
        for w in missing:
            print(f"  - {w}: no arrow chain found. A check that found nothing to "
                  f"check is not a green check.")
        return 1

    distinct = sorted(set(copies.values()))
    if len(distinct) > 1:
        print("claim-chain: THE COPIES DISAGREE")
        for where, chain in copies.items():
            print(f"  {where:<28} {chain.replace(chr(0x2192), ' -> ')}")
        print("\nThe chain is the shape of the pipeline and the map below draws it as "
              "phases. Make them one sentence, or make the page draw what it says.")
        return 1

    chain = distinct[0].replace("→", " -> ")
    print(f"claim-chain: {len(copies)} copies, all stating `{chain}`")
    return 0


if __name__ == "__main__":
    sys.exit(main())
