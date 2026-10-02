#!/usr/bin/env python3
"""Draw assets/app-flow.svg: the application, inside - one item followed through
both services (ADR-0103).

DRAWN, NOT GENERATED. Every other picture on the page is derived from infra/,
the chart or the bucket and held to its source by a gate; this one is drawn,
and the page says so in its own summary line. The coordinates are by hand; the
facts were read from the code the day it was drawn - the tables in
app/src/models.py and worker/alembic, the outbox relay in app/src/outbox.py,
the receipt's `on conflict do nothing` in worker/consumer/handler.py, the
three receipts before the dead-letter queue in infra/modules/queue. When one of
those changes, this file is edited by hand and rerun, and the page's builder
refuses a site/index.html that carries a different copy.

The marks are the page's own: `<use href="#ic-…">` into the sprite that
scripts/build-site-page.py inlines, so no icon is copied twice. The colours
are classes the template styles with the theme's variables, so the picture
follows light and dark the way the rest of the page does.

    python3 scripts/draw-app-flow.py      # -> assets/app-flow.svg
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "assets/app-flow.svg"
W, H = 1560, 984
s = []
A = s.append


def box(x, y, w, h, cls="af-tile"):
    A(f'<rect class="{cls}" x="{x}" y="{y}" width="{w}" height="{h}" rx="8"/>')


def head(x, y, title, sub, ico=None, size=40):
    tx = x + 16
    if ico:
        A(f'<use href="#ic-{ico}" x="{x + 14}" y="{y + 14}" width="{size}" height="{size}"/>')
        tx = x + 26 + size
    A(f'<text class="af-t" x="{tx}" y="{y + 32}">{title}</text>')
    if sub:
        A(f'<text class="af-s" x="{tx}" y="{y + 52}">{sub}</text>')


def part(x, y, w, h, title, sub=None):
    A(f'<rect class="af-part" x="{x}" y="{y}" width="{w}" height="{h}" rx="5"/>')
    A(f'<text class="af-pt" x="{x + 12}" y="{y + 22}">{title}</text>')
    if sub:
        A(f'<text class="af-ps" x="{x + 12}" y="{y + 40}">{sub}</text>')


def path(d, cls, m):
    A(f'<path class="{cls}" d="{d}" marker-end="url(#af-{m})"/>')


def step(n, x, y):
    A(f'<circle class="af-step" cx="{x}" cy="{y}" r="12"/><text class="af-sn" x="{x}" y="{y + 4.5}">{n}</text>')


def txt(x, y, t, cls, anchor="start"):
    A(f'<text class="{cls}" x="{x}" y="{y}" text-anchor="{anchor}">{t}</text>')


# everything below is drawn 40 px higher than the scratch mock: the heading is
# the summary line on the page, not part of the picture
DY = -40


def y(v):
    return v + DY


# legend
for i, (cls, t) in enumerate((("af-sync", "a request someone waits for"), ("af-async", "a message nobody waits for"),
                              ("af-failp", "a message that keeps failing"), ("af-cred", "credentials, read at start"))):
    x = 40 + i * 260
    A(f'<path class="{cls}" d="M{x},{y(69)} L{x + 34},{y(69)}"/>')
    txt(x + 42, y(74), t, "af-lg")

box(40, y(300), 180, 76); head(40, y(300), "Browser", "the visitor")
box(270, y(300), 210, 76); head(270, y(300), "Load balancer", "routes by path", "elb")

box(560, y(96), 330, 100); head(560, y(96), "web", "nginx · the interface", "ecs")
txt(626, y(176), "serves / · no database", "af-ps")

box(560, y(250), 330, 320); head(560, y(250), "api", "FastAPI · the domain", "ecs")
part(576, y(322), 298, 64, "HTTP handlers", "POST · GET · PATCH · DELETE")
part(576, y(400), 298, 64, "outbox relay · a thread", "sends what the outbox holds")
part(576, y(478), 298, 64, "results consumer · a thread", "reads what the worker reports")

box(980, y(294), 250, 76); head(980, y(294), "SQS · items", "item.created v1", "sqs")
box(980, y(474), 250, 76); head(980, y(474), "SQS · results", "item.processed v1", "sqs")
box(980, y(96), 250, 120, "af-fail"); head(980, y(96), "dead-letter queues", "one per queue", "sqs", 34)
txt(996, y(166), "after 3 failed receipts", "af-psbad")
A(f'<use href="#ic-cloudwatch" x="994" y="{y(172)}" width="20" height="20"/>')
txt(1020, y(186), "an alarm on each · no action", "af-ps")

box(1300, y(250), 230, 320); head(1300, y(250), "worker", "no port · no balancer", "ecs")
part(1316, y(322), 198, 100, "consume", "receive the event")
txt(1328, y(402), "write a receipt", "af-ps")
part(1316, y(436), 198, 106, "report", "publish item.processed")
txt(1328, y(516), "then delete the event", "af-ps")
box(1300, y(96), 230, 100); head(1300, y(96), "Secrets Manager", "database credentials", "secretsmanager")

box(560, y(690), 970, 280)
A(f'<rect class="af-schema" x="576" y="{y(706)}" width="664" height="150" rx="6"/>')
part(592, y(722), 200, 84, "demo_items", "the items")
part(808, y(722), 200, 84, "outbox", "events not yet sent")
part(1024, y(722), 200, 84, "item_processing", "what the worker reported")
txt(592, y(838), "schema public — written by the api only", "af-pt")
A(f'<rect class="af-schema" x="1256" y="{y(706)}" width="258" height="150" rx="6"/>')
part(1272, y(722), 226, 84, "receipts", "one per item · first wins")
txt(1272, y(838), "schema worker — the worker's", "af-pt")
A(f'<use href="#ic-rds" x="576" y="{y(878)}" width="40" height="40"/>')
txt(628, y(900), "RDS PostgreSQL", "af-t")
txt(628, y(920), "one database · two schemas · neither service reads the other's", "af-s")


def P(*pts):
    return "M" + " L".join(f"{a},{y(b)}" for a, b in pts)


path(P((220, 330), (266, 330)), "af-sync", "a"); step(1, 243, y(312))
path(P((480, 322), (572, 322)), "af-sync", "a"); step(2, 550, y(306)); txt(490, y(314), "/api/*", "af-el")
path(P((572, 352), (484, 352)), "af-sync af-back", "a"); step(4, 550, y(370))
path(P((266, 358), (224, 358)), "af-sync af-back", "a")
path(P((375, 300), (375, 146), (556, 146)), "af-sync", "a"); txt(386, y(230), "everything else → web", "af-el")
path(P((650, 570), (650, 718)), "af-sync", "a"); path(P((860, 570), (860, 718)), "af-sync", "a")
A(f'<path class="af-sync" d="{P((650, 628), (860, 628))}"/>'); step(3, 650, y(628))
txt(632, y(614), "one transaction:", "af-el", "end"); txt(632, y(632), "the item and its event,", "af-el", "end")
txt(632, y(650), "or neither", "af-el", "end")
path(P((874, 432), (930, 432), (930, 332), (976, 332)), "af-async", "g"); step(5, 930, y(380))
path(P((1230, 350), (1312, 350)), "af-async", "g"); step(6, 1270, y(334))
path(P((1415, 570), (1415, 718)), "af-sync", "a"); step(7, 1415, y(630))
txt(1400, y(656), "insert … on conflict do nothing", "af-el", "end")
path(P((1316, 500), (1234, 512)), "af-async", "g"); step(8, 1272, y(528))
path(P((980, 512), (878, 510)), "af-async", "g"); step(9, 930, y(494))
path(P((876, 570), (876, 672), (1124, 672), (1124, 718)), "af-sync", "a"); step(10, 1000, y(672))
path(P((1040, 294), (1040, 220)), "af-failp", "b"); path(P((1215, 474), (1215, 220)), "af-failp", "b")
path(P((1415, 196), (1415, 246)), "af-cred", "c")
path(P((1300, 236), (870, 236), (870, 246)), "af-cred", "c")


def mk(i, cls, sz=8):
    return (f'<marker id="af-{i}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="{sz}" markerHeight="{sz}" '
            f'orient="auto"><path class="{cls}" d="M0,0 L10,5 L0,10 z"/></marker>')


defs = "<defs>" + mk("a", "af-ma") + mk("g", "af-mg") + mk("b", "af-mb") + mk("c", "af-mc", 7) + "</defs>"
svg = (f'<svg class="appflow" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H + DY}" role="img" '
       f'aria-label="The application, inside: one item followed through the api, the queues and the worker">'
       + defs + "".join(s) + "</svg>\n")
OUT.write_text(svg)
print(f"{OUT.relative_to(ROOT)}: {len(svg.encode()):,} bytes")
