#!/usr/bin/env python3
"""The application, inside - generated (ADR-0104, replacing ADR-0103's drawing).

Writes assets/app-flow.html: the picture and the numbered steps under it, which
scripts/build-site-page.py injects into Details. Everything drawn is DERIVED:

  services.json          the services, their parts, the tables each owns, the
                         queues each part publishes and consumes, the routes,
                         which services hold database credentials, the event
                         each queue carries (its contract in contracts/)
  infra/modules/queue    how many failed receipts before the dead-letter queue,
                         and that an alarm watches it
  the code               every note a step carries is refused unless the file
                         it cites contains what it claims

The steps are not written anywhere. They are the walk a request takes: the
browser, the balancer's route, what the answering part writes, the answer; then
every part that reads what was written, the queue it publishes to, the part of
another service that consumes it, what that part writes and publishes - until
nothing new is reached. A step is numbered in the order the walk meets it.

assets/app-flow-layout.json says only where things go. A node or an arrow with
no place there is a refusal, and so is a place for something that no longer
exists - the picture cannot quietly drop a new queue or keep a dead one.

    python3 scripts/generate-app-flow.py           # -> assets/app-flow.html
    python3 scripts/generate-app-flow.py --check   # the drift gate; writes nothing
"""
from __future__ import annotations

import html
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "services.json"
LAYOUT = ROOT / "assets/app-flow-layout.json"
OUT = ROOT / "assets/app-flow.html"
QUEUE_MODULE = ROOT / "infra/modules/queue"


class Refusal(Exception):
    pass


def esc(s):
    return html.escape(str(s), quote=True)


def event_name(path: str) -> str:
    # contracts/item.created.v1.json -> item.created v1
    m = re.match(r".*/([a-z0-9_.]+)\.v(\d+)\.json$", path)
    if not m:
        raise Refusal(f"services.json: event contract {path} is not named <event>.v<n>.json")
    return f"{m.group(1)} v{m.group(2)}"


def queue_facts() -> tuple[int, bool]:
    variables = (QUEUE_MODULE / "variables.tf").read_text()
    m = re.search(r'variable "max_receive_count".*?default\s*=\s*(\d+)', variables, re.S)
    if not m:
        raise Refusal("infra/modules/queue: no max_receive_count default to say how many receipts before the dead-letter queue")
    main = (QUEUE_MODULE / "main.tf").read_text()
    alarmed = 'resource "aws_cloudwatch_metric_alarm"' in main
    silent = re.search(r"alarm_actions\s*=\s*\[\s*\]", main) is not None
    return int(m.group(1)), alarmed and silent


def human_list(xs):
    xs = [f"<code>{esc(x)}</code>" for x in xs]
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]


def build():
    man = json.loads(MANIFEST.read_text())
    lay = json.loads(LAYOUT.read_text())
    services = man["services"]
    events = man.get("events", {})
    by_name = {s["name"]: s for s in services}
    parts = {}
    for s in services:
        for p in s.get("parts", []):
            parts[f"{s['name']}/{p['name']}"] = (s, p)
    table_owner = {t: s for s in services for t in (s.get("database") or {}).get("tables", [])}
    routed = [s for s in services if s["routes"] and s["routes"] != ["default"]]
    default = [s for s in services if s["routes"] == ["default"]]
    if len(routed) != 1 or len(default) != 1:
        raise Refusal("the picture starts from one routed service and one default; services.json has "
                      f"{[s['name'] for s in routed]} and {[s['name'] for s in default]}")
    entry = routed[0]
    entry_parts = [k for k, (s, p) in parts.items() if s is entry and p["kind"] == "http"]
    if len(entry_parts) != 1:
        raise Refusal(f"{entry['name']} has {len(entry_parts)} http parts; the picture follows exactly one")
    max_receive, alarm_silent = queue_facts()
    notes = {k: v for k, v in lay.get("notes", {}).items() if not k.startswith("_")}
    for k, n in notes.items():
        ev = n["evidence"]
        if ev["contains"] not in (ROOT / ev["file"]).read_text(errors="replace"):
            raise Refusal(f"note on {k}: {ev['file']} does not contain {ev['contains']!r} - the sentence would claim what the code does not do")

    # ---- the walk
    edges, steps = [], []

    def edge(eid, kind, src, dst, text=None, numbered=True):
        n = None
        if numbered:
            steps.append((eid, text)); n = len(steps)
        edges.append({"id": eid, "kind": kind, "src": src, "dst": dst, "n": n})
        return n

    q_consumers = {}
    for k, (s, p) in parts.items():
        for q in p.get("consumes", []):
            q_consumers.setdefault(q, []).append(k)

    edge("request", "sync", "browser", "alb", "The browser asks.")
    routes = " and ".join(f"<code>{esc(r)}</code>" for r in entry["routes"])
    edge(f"route:{entry['name']}", "sync", "alb", f"service:{entry['name']}",
         f"The load balancer sends {routes} to the {esc(entry['name'])} and everything else to {esc(default[0]['name'])}.")
    edge(f"route-default:{default[0]['name']}", "sync", "alb", f"service:{default[0]['name']}", numbered=False)

    seen_parts, seen_tables = set(), set()

    def visit(key, how):
        if key in seen_parts:
            return
        seen_parts.add(key)
        s, p = parts[key]
        writes = p.get("writes", [])
        if len(writes) > 1:
            for t in writes:
                edge(f"write:{key}->{t}", "sync", f"part:{key}", f"table:{t}", numbered=False)
            edge(f"tx:{key}", "tx", f"part:{key}", None,
                 f"The {esc(s['name'])} writes {human_list(writes)} in one transaction: "
                 + ("both or neither." if len(writes) == 2 else "all or none."))
        elif writes:
            t = writes[0]
            verb = "writes" if how == "request" else ("And writes" if how == "deliver" else "Writes")
            edge(f"write:{key}->{t}", "sync", f"part:{key}", f"table:{t}",
                 f"{verb} {human_list(writes)}, in the {esc(s['name'])}'s own schema." + _note(f"write:{key}->{t}"))
        seen_tables.update(writes)
        if how == "request":
            edge(f"response:{s['name']}", "sync back", f"service:{s['name']}", "alb",
                 "And answers. The visitor's wait ends here.")
            edges.append({"id": "response-browser", "kind": "sync back", "src": "alb", "dst": "browser", "n": None})
        for q in p.get("publishes", []):
            reads = p.get("reads", [])
            lead = (f"The {esc(s['name'])}'s {esc(p['name'])}, a thread of its own, sends what {human_list(reads)} holds"
                    if reads else "It publishes")
            edge(f"publish:{key}->{q}", "async", f"part:{key}", f"queue:{q}",
                 f"{lead} to the <code>{esc(q)}</code> queue as <code>{esc(event_name(events[q]))}</code>."
                 + _note(f"publish:{key}->{q}"))
            for c in q_consumers.get(q, []):
                cs, cp = parts[c]
                edge(f"deliver:{q}->{c}", "async", f"queue:{q}", f"part:{c}",
                     f"The {esc(cs['name'])}'s {esc(cp['name'])} receives it.")
                visit(c, "deliver")
        # a loop that reads what this part wrote goes next
        for k2, (s2, p2) in parts.items():
            if k2 not in seen_parts and set(p2.get("reads", [])) & set(writes):
                visit(k2, "read")

    def _note(eid):
        n = notes.get(eid)
        return (" " + esc(n["text"])) if n else ""

    visit(entry_parts[0], "request")
    unreached = [k for k, (s, p) in parts.items() if k not in seen_parts and p["kind"] == "loop"]
    if unreached:
        raise Refusal(f"parts no request reaches: {unreached} - the walk from the browser never gets to them")
    for q in q_consumers:
        edges.append({"id": f"dlq:{q}", "kind": "failp", "src": f"queue:{q}", "dst": "dlq", "n": None})
    for s in services:
        if s.get("database"):
            edges.append({"id": f"cred:{s['name']}", "kind": "cred", "src": "secrets", "dst": f"service:{s['name']}", "n": None})

    # ---- every drawn thing has a place, and every place a thing
    nodes = {"browser", "alb", "dlq", "secrets", "db"}
    nodes |= {f"service:{s['name']}" for s in services}
    nodes |= {f"queue:{q}" for q in q_consumers}
    nodes |= {f"schema:{s['database']['schema']}" for s in services if s.get("database")}
    nodes |= {f"part:{k}" for k, (s, p) in parts.items() if s is not by_name.get(default[0]["name"])}
    nodes |= {f"table:{t}" for t in table_owner}
    placed = {k for k in lay["nodes"]}
    drawn = {e["id"] for e in edges}
    routed_ids = {k for k in lay["edges"]}
    problems = [f"{n} has no place in {LAYOUT.name}" for n in sorted(nodes - placed)]
    problems += [f"{LAYOUT.name} places {n}, which nothing draws" for n in sorted(placed - nodes)]
    problems += [f"arrow {e} has no route in {LAYOUT.name}" for e in sorted(drawn - routed_ids)]
    problems += [f"{LAYOUT.name} routes {e}, which no arrow is" for e in sorted(routed_ids - drawn)]
    problems += [f"note on {k} names an arrow that is not drawn" for k in notes if k not in drawn]
    if problems:
        raise Refusal("\n".join(problems))
    return man, lay, services, by_name, parts, table_owner, events, edges, steps, max_receive, alarm_silent, default[0]


def render():
    man, lay, services, by_name, parts, table_owner, events, edges, steps, max_receive, alarm_silent, web = build()
    N, E = lay["nodes"], lay["edges"]
    s = []
    A = s.append

    def box(key, cls="af-tile"):
        x, y, w, h = N[key]
        A(f'<rect class="{cls}" x="{x}" y="{y}" width="{w}" height="{h}" rx="8"/>')
        return x, y, w, h

    def head(x, y, title, sub, ico=None, size=40):
        tx = x + 16
        if ico:
            A(f'<use href="#ic-{ico}" x="{x + 14}" y="{y + 14}" width="{size}" height="{size}"/>'); tx = x + 26 + size
        A(f'<text class="af-t" x="{tx}" y="{y + 32}">{esc(title)}</text>')
        if sub:
            A(f'<text class="af-s" x="{tx}" y="{y + 52}">{esc(sub)}</text>')

    def text(x, y, t, cls, anchor="start"):
        A(f'<text class="{cls}" x="{x}" y="{y}" text-anchor="{anchor}">{esc(t)}</text>')

    def part_box(key, title, lines):
        x, y, w, h = N[key]
        A(f'<rect class="af-part" x="{x}" y="{y}" width="{w}" height="{h}" rx="5"/>')
        text(x + 12, y + 22, title, "af-pt")
        for i, ln in enumerate(lines):
            text(x + 12, y + 40 + i * 18, ln, "af-ps")

    for i, (cls, t) in enumerate((("af-sync", "a request someone waits for"), ("af-async", "a message nobody waits for"),
                                  ("af-failp", "a message that keeps failing"), ("af-cred", "credentials, read at start"))):
        x = 40 + i * 260
        A(f'<path class="{cls}" d="M{x},29 L{x + 34},29"/>'); text(x + 42, 34, t, "af-lg")

    x, y, *_ = box("browser"); head(x, y, "Browser", "the visitor")
    x, y, *_ = box("alb"); head(x, y, "Load balancer", "routes by path", "elb")
    for sv in services:
        x, y, w, h = box(f"service:{sv['name']}")
        head(x, y, sv["name"], lay["labels"].get(sv["name"], ""), "ecs")
        if sv is web:
            what = " · ".join([f"serves {r}" if r != "default" else "serves /" for r in sv["routes"]]
                              + ["no database" if not sv.get("database") else "a database"])
            text(x + 66, y + 80, what, "af-ps")
    for k, (sv, p) in parts.items():
        if sv is web:
            continue
        lines = []
        if p.get("consumes"): lines.append("receives " + ", ".join(p["consumes"]))
        if p.get("reads"): lines.append("reads " + ", ".join(p["reads"]))
        if p.get("writes"): lines.append("writes " + ", ".join(p["writes"]))
        if p.get("publishes"): lines.append("publishes to " + ", ".join(p["publishes"]))
        if p["kind"] == "http": lines = ["answers " + " · ".join(sv["routes"])] + lines[:1]
        title = p["name"] + (" · a thread" if p["kind"] == "loop" and len([1 for _, (s2, _) in parts.items() if s2 is sv]) > 1 else "")
        part_box(f"part:{k}", title, lines[:3] if N[f"part:{k}"][3] < 100 else lines)
    for q in sorted({e["src"].split(":", 1)[1] for e in edges if e["kind"] == "failp"}):
        x, y, *_ = box(f"queue:{q}"); head(x, y, f"SQS · {q}", event_name(man["events"][q]), "sqs")
    x, y, *_ = box("dlq", "af-fail"); head(x, y, "dead-letter queues", "one per queue", "sqs", 34)
    text(x + 16, y + 70, f"after {max_receive} failed receipts", "af-psbad")
    if alarm_silent:
        A(f'<use href="#ic-cloudwatch" x="{x + 14}" y="{y + 76}" width="20" height="20"/>')
        text(x + 40, y + 90, "an alarm on each · no action", "af-ps")
    x, y, *_ = box("secrets"); head(x, y, "Secrets Manager", "database credentials", "secretsmanager")
    x, y, w, h = box("db")
    owners = [sv for sv in services if sv.get("database")]
    for sv in owners:
        sch = sv["database"]["schema"]
        sx, sy, sw, sh = N[f"schema:{sch}"]
        A(f'<rect class="af-schema" x="{sx}" y="{sy}" width="{sw}" height="{sh}" rx="6"/>')
        text(sx + 16, sy + sh - 18, f"schema {sch} · {sv['name']} only", "af-pt")
        for t in sv["database"]["tables"]:
            tx, ty, tw, th = N[f"table:{t}"]
            A(f'<rect class="af-part" x="{tx}" y="{ty}" width="{tw}" height="{th}" rx="5"/>')
            text(tx + 12, ty + 22, t, "af-pt")
    A(f'<use href="#ic-rds" x="{x + 16}" y="{y + h - 72}" width="40" height="40"/>')
    text(x + 68, y + h - 50, "RDS PostgreSQL", "af-t")
    text(x + 68, y + h - 30, f"one database · {len(owners)} schemas · no service reads another's", "af-s")

    marker = {"sync": "a", "sync back": "a", "tx": None, "async": "g", "failp": "b", "cred": "c"}
    cls = {"sync": "af-sync", "sync back": "af-sync af-back", "tx": "af-sync", "async": "af-async", "failp": "af-failp", "cred": "af-cred"}
    for e in edges:
        r = E[e["id"]]
        d = "M" + " L".join(f"{a},{b}" for a, b in r["path"])
        m = marker[e["kind"]]
        A(f'<path class="{cls[e["kind"]]}" d="{d}"' + (f' marker-end="url(#af-{m})"' if m else "") + "/>")
    for e in edges:
        r = E[e["id"]]
        if e["id"].startswith("route:") and "label" in r:
            sv = by_name[e["id"].split(":", 1)[1]]
            text(*r["label"], " ".join(rr for rr in sv["routes"] if rr.endswith("*")) or sv["routes"][0], "af-el")
        if e["id"].startswith("route-default:") and "label" in r:
            text(*r["label"], f"everything else → {e['id'].split(':', 1)[1]}", "af-el")
        if e["id"].startswith("tx:") and "label" in r:
            lx, ly = r["label"]
            for i, ln in enumerate(("one transaction:", "both or neither")):
                text(lx, ly + i * 18, ln, "af-el", "end")
        notes = json.loads(LAYOUT.read_text()).get("notes", {})
        if e["id"] in notes and notes[e["id"]].get("label") and "label" in r:
            text(*r["label"], notes[e["id"]]["label"], "af-el", "end")
    for e in edges:
        if e["n"]:
            sx, sy = E[e["id"]]["step"]
            A(f'<circle class="af-step" cx="{sx}" cy="{sy}" r="12"/><text class="af-sn" x="{sx}" y="{sy + 4.5}">{e["n"]}</text>')

    def mk(i, c, sz=8):
        return (f'<marker id="af-{i}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="{sz}" markerHeight="{sz}" '
                f'orient="auto"><path class="{c}" d="M0,0 L10,5 L0,10 z"/></marker>')

    defs = "<defs>" + mk("a", "af-ma") + mk("g", "af-mg") + mk("b", "af-mb") + mk("c", "af-mc", 7) + "</defs>"
    svg = (f'<svg class="appflow" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {lay["width"]} {lay["height"]}" role="img" '
           f'aria-label="The application, inside: one request followed through every service it reaches">' + defs + "".join(s) + "</svg>")
    ol = "<ol class=\"appflow-steps\">" + "".join(f"<li>{t}</li>" for _, t in steps) + "</ol>"
    tail = (f'<p class="sub">A service that is down loses nothing: its events wait in the queue. An event that fails '
            f'{max_receive} times moves to its dead-letter queue' + (", where an alarm waits." if alarm_silent else ".") + "</p>")
    return ('<!-- GENERATED by scripts/generate-app-flow.py from services.json, infra/modules/queue and the code it cites, '
            'placed by assets/app-flow-layout.json. Do not edit. -->\n'
            f'<div class="appflow-wrap">{svg}</div>\n{ol}\n{tail}\n')


def main(argv):
    try:
        out = render()
    except Refusal as e:
        print(f"app-flow: REFUSED\n{e}", file=sys.stderr)
        return 1
    if "--check" in argv:
        if not OUT.is_file() or OUT.read_text() != out:
            print("app-flow: assets/app-flow.html is not what services.json, the layout and the code give - run scripts/generate-app-flow.py", file=sys.stderr)
            return 1
        print("app-flow: clean")
        return 0
    OUT.write_text(out)
    print(f"app-flow: wrote {OUT.relative_to(ROOT)} - {out.count('<li>')} steps, {len(out.encode()):,} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
