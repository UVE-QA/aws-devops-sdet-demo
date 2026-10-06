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

import ast
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
OBSERVE = ROOT / "scripts/observe-environment.sh"
TEMPLATE = ROOT / "assets/index.template.html"


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


def interface_calls(body: str) -> list[tuple[str, str]]:
    """What an interface file asks the api for: (method, path), read from its
    fetch calls and the /api/ paths it names. A template's ${...} becomes {id};
    a query string is dropped."""
    calls = []
    for m in re.finditer(r"fetch\(\s*([`\"'])(.*?)\1", body):
        path = re.sub(r"\$\{[^}]*\}", "{id}", m.group(2)).split("?")[0]
        tail = body[m.end():m.end() + 160]
        mm = re.match(r"\s*,\s*\{[^}]*?method:\s*[\"'](\w+)[\"']", tail, re.S)
        calls.append(((mm.group(1) if mm else "GET").upper(), path))
    named = {p for _, p in calls}
    for path in re.findall(r"[\"'](/api/[a-z0-9/_-]+)[\"']", body):
        if path not in named:
            calls.append(("GET", path)); named.add(path)
    return [c for c in dict.fromkeys(calls) if c[1].startswith("/")]


VERBS = {("GET", False): "lists", ("POST", False): "adds", ("GET", True): "reads",
         ("PATCH", True): "edits", ("PUT", True): "edits", ("DELETE", True): "deletes"}


def interface_purpose(calls: list[tuple[str, str]]) -> tuple[list[str], str]:
    """(verbs, resource) for the one resource the interface changes - `lists,
    adds, edits, deletes` and `items`. A path only read, like a health check,
    is not what the interface is for."""
    by_res = {}
    for meth, path in calls:
        m = re.match(r"/api/([a-z_]+)(/\{id\})?$", path)
        if m and (meth, bool(m.group(2))) in VERBS:
            by_res.setdefault(m.group(1), []).append(VERBS[(meth, bool(m.group(2)))])
    changed = {r: [v for v in dict.fromkeys(vs) if v != "reads"] for r, vs in by_res.items()
               if set(vs) & {"adds", "edits", "deletes"}}
    if len(changed) != 1:
        return [], ""
    (res, verbs), = changed.items()
    return verbs, res


def said(verbs: list[str]) -> str:
    return verbs[0] if len(verbs) == 1 else ", ".join(verbs[:-1]) + " and " + verbs[-1]


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

    routes = " and ".join(f"<code>{esc(r)}</code>" for r in entry["routes"])
    web, en = default[0]["name"], entry["name"]
    # THE INTERFACE CALLS THE API FROM THE BROWSER (2026-10-06). A default
    # service whose part says it serves an interface that `calls` the routed
    # one is where the walk starts: the page first, then what its script asks.
    # The claim is held to the interface file - it must fetch one of the
    # routed service's paths - or the picture would draw a call nobody makes.
    caller = [(k, p) for k, (s, p) in parts.items() if s is default[0] and en in p.get("calls", [])]
    starred = [r for r in entry["routes"] if r.endswith("*")]
    if caller:
        iface = caller[0][1].get("interface")
        if not iface or not (ROOT / iface).is_file():
            raise Refusal(f"services.json: {web}'s part says it calls the {en} but names no interface file that exists")
        body = (ROOT / iface).read_text(errors="replace")
        if "fetch(" not in body or not any(r[:-1] in body for r in starred):
            raise Refusal(f"{iface} fetches none of {starred} - the picture would draw a call the interface does not make")
        asked = " and ".join(f"<code>{esc(r)}</code>" for r in starred) or routes
        verbs, res = interface_purpose(interface_calls(body))
        purpose = f"{said(verbs)} {res}" if verbs else ""
        fname = iface.rsplit("/", 1)[-1]
        edge("request", "sync", "browser", "alb", "The browser asks for the page.")
        edge(f"route-default:{web}", "sync", "alb", f"service:{web}",
             f"The load balancer sends it to {esc(web)}, the default for every path that is not the {esc(en)}'s.")
        edge(f"response:{web}", "sync back", f"service:{web}", "alb",
             f"{esc(web).capitalize()} answers with <code>{esc(fname)}</code> and its script, files from nginx and "
             f"nothing else, and the browser runs them: that is the interface"
             + (f", which {esc(purpose)}" if purpose else "") + f". {esc(web).capitalize()} never calls the {esc(en)}.")
        edges.append({"id": f"response-browser:{web}", "kind": "sync back", "src": "alb", "dst": "browser", "n": None})
        edge(f"call:{web}", "sync", f"interface:{web}", "alb",
             f"The interface asks for {asked} at the same address it came from.")
        edge(f"route:{en}", "sync", "alb", f"service:{en}",
             f"The load balancer sends {asked} to the {esc(en)}.", numbered=False)
    else:
        edge("request", "sync", "browser", "alb", "The browser asks.")
        edge(f"route:{en}", "sync", "alb", f"service:{en}",
             f"The load balancer sends {routes} to the {esc(en)} and everything else to {esc(web)}.")
        edge(f"route-default:{web}", "sync", "alb", f"service:{web}", numbered=False)

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
            edges.append({"id": "response-browser", "kind": "sync back", "src": "alb",
                          "dst": f"interface:{web}" if caller else "browser", "n": None})
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
    # THE LOOP CLOSES WHERE IT STARTED: a table the answering part reads and
    # another part writes is how what happened after the answer gets back to
    # the visitor - on the next read.
    ek = entry_parts[0]
    ep = parts[ek][1]
    for t in ep.get("reads", []):
        if t in ep.get("writes", []):
            continue
        if any(t in p2.get("writes", []) for k2, (_, p2) in parts.items() if k2 != ek):
            edge(f"read:{ek}<-{t}", "sync back", f"table:{t}", f"part:{ek}",
                 f"The next read shows it: what the {esc(en)} answers for "
                 + (" and ".join(f"<code>{esc(r)}</code>" for r in starred) or routes)
                 + f" carries <code>{esc(t)}</code>'s row with each item." + _note(f"read:{ek}<-{t}"))
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
    if caller:
        nodes.add(f"interface:{web}")
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

    # ---- what each step lights: its arrow, the unnumbered arrows its sentence
    # also speaks of, and the boxes at their ends
    groups = {}
    for n, (eid, _) in enumerate(steps, 1):
        ids = [eid]
        if eid.startswith("route:") and not any(x.startswith("route-default:") for x, _ in steps):
            ids += [e["id"] for e in edges if e["id"].startswith("route-default:")]
        if eid.startswith("tx:"):
            ids += [e["id"] for e in edges if e["id"].startswith(f"write:{eid[3:]}->")]
        if eid.startswith("response:"):
            ids.append(f"response-browser:{eid[9:]}" if eid[9:] == web and caller else "response-browser")
        if eid.startswith("call:"):
            ids += [e["id"] for e in edges if e["id"].startswith("route:")]
        ends = []
        for e in edges:
            if e["id"] in ids:
                for k in (e["src"], e["dst"]):
                    if k and k not in ends:
                        ends.append(k)
        groups[n] = {"e": ids, "n": ends}
    iface_info = None
    if caller:
        iface_info = {"file": caller[0][1]["interface"], "calls": interface_calls(body), "purpose": purpose,
                      "verbs": verbs, "res": res, "service": web, "calls_service": en}
    return man, lay, services, by_name, parts, table_owner, events, edges, steps, max_receive, alarm_silent, default[0], groups, iface_info


# ---- the cards: what a box is, read from the same sources as the picture

def repo() -> str:
    m = re.search(r'var REPO = "([^"]+)"', TEMPLATE.read_text())
    if not m:
        raise Refusal(f"{TEMPLATE.name}: no `var REPO = \"owner/name\"` to link the code from")
    return m.group(1)


def line_of(path: str, needle: str) -> int:
    for i, ln in enumerate((ROOT / path).read_text(errors="replace").splitlines(), 1):
        if needle in ln:
            return i
    raise Refusal(f"{path} does not contain {needle!r} - a card would link to a line that is not there")


def columns(service: dict, table: str) -> tuple[str, int, list[str]]:
    """The table's columns, from the model or the migration that declares it -
    the same declarations manifest-check holds the table names to."""
    files = sorted((ROOT / service["context"]).rglob("*.py"))
    trees = [(str(f.relative_to(ROOT)), ast.parse(f.read_text(errors="replace"))) for f in files]
    # a model says what the table is now; a first migration only what it was
    for rel, tree in trees:
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                named = any(isinstance(b, ast.Assign) and any(getattr(t, "id", "") == "__tablename__" for t in b.targets)
                            and isinstance(b.value, ast.Constant) and b.value.value == table for b in node.body)
                if named:
                    cols = [b.target.id for b in node.body if isinstance(b, ast.AnnAssign) and isinstance(b.target, ast.Name)
                            and isinstance(b.value, ast.Call) and getattr(b.value.func, "id", "") in ("mapped_column", "Column")]
                    if cols:
                        return rel, node.lineno, cols
    for rel, tree in trees:
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "create_table" and node.args
                    and isinstance(node.args[0], ast.Constant) and node.args[0].value == table):
                cols = [a.args[0].value for a in node.args[1:] if isinstance(a, ast.Call) and getattr(a.func, "attr", "") == "Column"
                        and a.args and isinstance(a.args[0], ast.Constant)]
                if cols:
                    return rel, node.lineno, cols
    raise Refusal(f"no model or migration under {service['context']}/ declares the columns of {table}")


def contract_fields(path: str) -> list[str]:
    def walk(sch, prefix):
        out = []
        for k, v in (sch.get("properties") or {}).items():
            out += walk(v, f"{prefix}{k}.") if v.get("type") == "object" and v.get("properties") else [prefix + k]
        return out
    return walk(json.loads((ROOT / path).read_text()), "")


def cards(services, parts, table_owner, events, edges, max_receive, alarm_silent):
    base = f"https://github.com/{repo()}"
    blob = lambda path, line=None: f"{base}/blob/main/{path}" + (f"#L{line}" if line else "")
    tree = lambda path: f"{base}/tree/main/{path}"
    code = lambda xs: ", ".join(f"<code>{esc(x)}</code>" for x in xs)
    by_part = lambda what, x: [k for k, (_, p) in parts.items() if x in p.get(what, [])]
    pname = lambda k: f"{esc(parts[k][0]['name'])} · {esc(parts[k][1]['name'])}"
    out = {}
    alb_file = "infra/modules/alb/main.tf"
    routed = [s for s in services if s["routes"] and s["routes"] != ["default"]]
    out["alb"] = {"t": "Load balancer", "s": "routes by path",
                  "r": [[f"{code(s['routes'])}", f"to the {esc(s['name'])}"] for s in routed]
                  + [["everything else", f"to the {esc(s['name'])}"] for s in services if s["routes"] == ["default"]],
                  "l": [["the listener and its rules", blob(alb_file, line_of(alb_file, 'resource "aws_lb_listener'))]]}
    for s in services:
        db = s.get("database")
        rows = [["image", f"<code>{esc(s['image'])}</code>, built from <code>{esc(s['context'])}/</code>"],
                ["port", esc(s["port"]) if s["port"] else "none, behind no balancer"],
                ["health", f"<code>{esc(s['health'])}</code>"]]
        if s["routes"]:
            rows.append(["answers", code(s["routes"]) if s["routes"] != ["default"] else "everything the others do not"])
        rows.append(["inside", ", ".join(esc(p["name"]) for p in s.get("parts", []))])
        for p in s.get("parts", []):
            if p.get("interface"):
                rows.append(["interface", f"<code>{esc(p['interface'])}</code>, run in the browser"
                             + (f"; it calls the {', '.join(esc(c) for c in p.get('calls', []))} from there" if p.get("calls") else "")])
        rows.append(["data", f"schema <code>{esc(db['schema'])}</code>: {code(db['tables'])}" if db else "no database"])
        if s.get("suites"):
            rows.append(["tested by", code(s["suites"])])
        links = [["its code", tree(s["context"])]] + [["the interface", blob(p["interface"])] for p in s.get("parts", []) if p.get("interface")]
        if db:
            links.append(["its migrations", tree(db["migrations"])])
        out[f"service:{s['name']}"] = {"t": s["name"], "s": "a service", "r": rows, "l": links}
    for k, (s, p) in parts.items():
        if not p.get("writes") and not p.get("publishes") and not p.get("consumes") and not p.get("reads") and p["kind"] == "http" and not s.get("database"):
            continue
        rows = [["runs", "answers requests" if p["kind"] == "http" else "on its own, in a loop"],
                ["code", f"<code>{esc(p['symbol'])}</code> in <code>{esc(p['file'])}</code>"]]
        for what, label in (("consumes", "receives from"), ("reads", "reads"), ("writes", "writes"), ("publishes", "publishes to")):
            if p.get(what):
                rows.append([label, code(p[what])])
        needle = p["symbol"] if p["kind"] == "http" and " " in p["symbol"] else None
        line = line_of(p["file"], needle) if needle else next(
            (i for i, ln in enumerate((ROOT / p["file"]).read_text().splitlines(), 1)
             if re.match(rf"\s*(async\s+def|def|class)\s+{re.escape(p['symbol'])}\b", ln)), None)
        if line is None:
            raise Refusal(f"{p['file']} defines no {p['symbol']} - the card would link nowhere")
        out[f"part:{k}"] = {"t": p["name"], "s": f"inside the {s['name']}", "r": rows, "l": [["open the code", blob(p["file"], line)]]}
    queue_main = str((QUEUE_MODULE / "main.tf").relative_to(ROOT))
    for q in sorted({e["src"].split(":", 1)[1] for e in edges if e["kind"] == "failp"}):
        rows = [["carries", f"<code>{esc(event_name(events[q]))}</code>"],
                ["fields", code(contract_fields(events[q]))],
                ["from", ", ".join(pname(k) for k in by_part("publishes", q))],
                ["to", ", ".join(pname(k) for k in by_part("consumes", q))],
                ["on failure", f"after {max_receive} failed receipts, to its dead-letter queue"]]
        out[f"queue:{q}"] = {"t": f"SQS · {q}", "s": "a queue", "r": rows,
                             "l": [["the event's contract", blob(events[q])], ["the queue module", blob(queue_main)]]}
    out["dlq"] = {"t": "dead-letter queues", "s": "one per queue",
                  "r": [["receives", f"an event that failed {max_receive} times"],
                        ["watched by", "an alarm on each, with no action yet" if alarm_silent else "an alarm on each"]],
                  "l": [["the queue module", blob(queue_main, line_of(queue_main, "redrive_policy"))]]}
    rds = "infra/modules/rds/main.tf"
    holders = [s["name"] for s in services if s.get("database")]
    out["secrets"] = {"t": "Secrets Manager", "s": "database credentials",
                      "r": [["read by", ", ".join(esc(h) for h in holders) + ", once, at start"]],
                      "l": [["where the secret is made", blob(rds, line_of(rds, 'resource "aws_secretsmanager_secret"'))]]}
    out["db"] = {"t": "RDS PostgreSQL", "s": "one database",
                 "r": [[f"schema <code>{esc(s['database']['schema'])}</code>", f"the {esc(s['name'])}'s only: {code(s['database']['tables'])}"]
                       for s in services if s.get("database")] + [["rule", "no service reads another's schema"]],
                 "l": [["the database module", blob(rds, line_of(rds, 'resource "aws_db_instance"'))]]}
    for t, s in table_owner.items():
        f, line, cols = columns(s, t)
        rows = [["owner", f"the {esc(s['name'])}, schema <code>{esc(s['database']['schema'])}</code>"],
                ["columns", code(cols)]]
        w, r = by_part("writes", t), by_part("reads", t)
        if w:
            rows.append(["written by", ", ".join(pname(k) for k in w)])
        if r:
            rows.append(["read by", ", ".join(pname(k) for k in r)])
        out[f"table:{t}"] = {"t": t, "s": "a table", "r": rows, "l": [["where it is declared", blob(f, line)]]}
    return out


def render():
    man, lay, services, by_name, parts, table_owner, events, edges, steps, max_receive, alarm_silent, web, groups, iface = build()
    N, E = lay["nodes"], lay["edges"]
    s = []
    A = s.append

    # Every box sits in a group named by its key and every arrow carries its id,
    # so the page can light one step and dim the rest without knowing geometry.
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

    def text(x, y, t, cls, anchor="start", edge=None):
        de = f' data-e="{esc(edge)}"' if edge else ""
        A(f'<text class="{cls}" x="{x}" y="{y}" text-anchor="{anchor}"{de}>{esc(t)}</text>')

    def group(key):
        A(f'<g data-n="{esc(key)}">')

    def end():
        A("</g>")

    def part_box(key, title, lines):
        x, y, w, h = N[key]
        group(key)
        A(f'<rect class="af-part" x="{x}" y="{y}" width="{w}" height="{h}" rx="5"/>')
        text(x + 12, y + 22, title, "af-pt")
        for i, ln in enumerate(lines):
            text(x + 12, y + 40 + i * 18, ln, "af-ps")
        end()

    for i, (cls, t) in enumerate((("af-sync", "a request someone waits for"), ("af-async", "a message nobody waits for"),
                                  ("af-failp", "a message that keeps failing"), ("af-cred", "credentials, read at start"))):
        x = 40 + i * 260
        A(f'<path class="{cls}" d="M{x},29 L{x + 34},29"/>'); text(x + 42, 34, t, "af-lg")

    group("browser"); x, y, *_ = box("browser"); head(x, y, "Browser", "the visitor's"); end()
    if iface:
        ik = f"interface:{iface['service']}"
        lines = [f"{iface['file'].rsplit('/', 1)[-1]}, from {iface['service']}"]
        if iface["verbs"]:
            lines += [", ".join(iface["verbs"]), f"{iface['res']} through the {iface['calls_service']}"]
        else:
            lines.append(f"asks the {iface['calls_service']}")
        part_box(ik, "the interface", lines)
    group("alb"); x, y, *_ = box("alb"); head(x, y, "Load balancer", "routes by path", "elb"); end()
    for sv in services:
        group(f"service:{sv['name']}")
        x, y, w, h = box(f"service:{sv['name']}")
        head(x, y, sv["name"], lay["labels"].get(sv["name"], ""), "ecs")
        if sv is web:
            served = f"serves {iface['file'].rsplit('/', 1)[-1]} and its script" if iface else (
                " · ".join(f"serves {r}" if r != "default" else "serves /" for r in sv["routes"]))
            what = served + " · " + ("no database" if not sv.get("database") else "a database")
            text(x + 66, y + 80, what, "af-ps")
        end()
    for k, (sv, p) in parts.items():
        if sv is web:
            continue
        lines = []
        if p.get("consumes"): lines.append("receives " + ", ".join(p["consumes"]))
        if p.get("reads"): lines.append("reads " + ", ".join(p["reads"]))
        if p.get("writes"): lines.append("writes " + ", ".join(p["writes"]))
        if p.get("publishes"): lines.append("publishes to " + ", ".join(p["publishes"]))
        if p["kind"] == "http": lines = ["answers " + " · ".join(sv["routes"])] + [ln for ln in lines if ln.startswith("writes")][:1]
        title = p["name"] + (" · a thread" if p["kind"] == "loop" and len([1 for _, (s2, _) in parts.items() if s2 is sv]) > 1 else "")
        part_box(f"part:{k}", title, lines[:3] if N[f"part:{k}"][3] < 100 else lines)
    for q in sorted({e["src"].split(":", 1)[1] for e in edges if e["kind"] == "failp"}):
        group(f"queue:{q}"); x, y, *_ = box(f"queue:{q}"); head(x, y, f"SQS · {q}", event_name(man["events"][q]), "sqs"); end()
    group("dlq")
    x, y, *_ = box("dlq", "af-fail"); head(x, y, "dead-letter queues", "one per queue", "sqs", 34)
    text(x + 16, y + 70, f"after {max_receive} failed receipts", "af-psbad")
    if alarm_silent:
        A(f'<use href="#ic-cloudwatch" x="{x + 14}" y="{y + 76}" width="20" height="20"/>')
        text(x + 40, y + 90, "an alarm on each · no action", "af-ps")
    end()
    group("secrets"); x, y, *_ = box("secrets"); head(x, y, "Secrets Manager", "database credentials", "secretsmanager"); end()
    group("db")
    x, y, w, h = box("db")
    owners = [sv for sv in services if sv.get("database")]
    end()
    for sv in owners:
        sch = sv["database"]["schema"]
        sx, sy, sw, sh = N[f"schema:{sch}"]
        group(f"schema:{sch}")
        A(f'<rect class="af-schema" x="{sx}" y="{sy}" width="{sw}" height="{sh}" rx="6"/>')
        text(sx + 16, sy + sh - 18, f"schema {sch} · {sv['name']} only", "af-pt")
        end()
        for t in sv["database"]["tables"]:
            tx, ty, tw, th = N[f"table:{t}"]
            group(f"table:{t}")
            A(f'<rect class="af-part" x="{tx}" y="{ty}" width="{tw}" height="{th}" rx="5"/>')
            text(tx + 12, ty + 22, t, "af-pt")
            end()
    group("db")
    A(f'<use href="#ic-rds" x="{x + 16}" y="{y + h - 72}" width="40" height="40"/>')
    text(x + 68, y + h - 50, "RDS PostgreSQL", "af-t")
    text(x + 68, y + h - 30, f"one database · {len(owners)} schemas · no service reads another's", "af-s")
    end()

    marker = {"sync": "a", "sync back": "a", "tx": None, "async": "g", "failp": "b", "cred": "c"}
    cls = {"sync": "af-sync", "sync back": "af-sync af-back", "tx": "af-sync", "async": "af-async", "failp": "af-failp", "cred": "af-cred"}
    for e in edges:
        r = E[e["id"]]
        d = "M" + " L".join(f"{a},{b}" for a, b in r["path"])
        m = marker[e["kind"]]
        A(f'<path class="{cls[e["kind"]]}" data-e="{esc(e["id"])}" d="{d}"' + (f' marker-end="url(#af-{m})"' if m else "") + "/>")
    notes = lay.get("notes", {})
    for e in edges:
        r = E[e["id"]]
        if e["id"].startswith("route:") and "label" in r:
            sv = by_name[e["id"].split(":", 1)[1]]
            text(*r["label"], " ".join(rr for rr in sv["routes"] if rr.endswith("*")) or sv["routes"][0], "af-el", edge=e["id"])
        if e["id"].startswith("route-default:") and "label" in r:
            text(*r["label"], f"everything else → {e['id'].split(':', 1)[1]}", "af-el", edge=e["id"])
        if e["id"].startswith("tx:") and "label" in r:
            lx, ly = r["label"]
            for i, ln in enumerate(("one transaction:", "both or neither")):
                text(lx, ly + i * 18, ln, "af-el", "end", edge=e["id"])
        if e["id"] in notes and notes[e["id"]].get("label") and "label" in r:
            text(*r["label"], notes[e["id"]]["label"], "af-el", "end", edge=e["id"])

    # What can be opened, drawn last so a box inside another is picked first:
    # the database under its tables, a service under its parts.
    info = cards(services, parts, table_owner, events, edges, max_receive, alarm_silent)
    if iface:
        info[f"interface:{iface['service']}"] = {
            "t": "the interface", "s": "runs in the visitor's browser",
            "r": [["file", f"<code>{esc(iface['file'])}</code>, served by {esc(iface['service'])}"],
                  ["does", esc(iface["purpose"]) or "-"],
                  ["asks", ", ".join(f"<code>{esc(m)} {esc(p)}</code>" for m, p in iface["calls"])],
                  ["answers come", f"from the {esc(iface['calls_service'])}, through the load balancer, at the same address"]],
            "l": [["open the interface", f"https://github.com/{repo()}/blob/main/{iface['file']}"]]}
    order = (["db"] + [f"service:{sv['name']}" for sv in services] + ["alb", "secrets", "dlq"]
             + [k for k in info if k.startswith("interface:")]
             + sorted(k for k in info if k.startswith("queue:")) + [f"part:{k}" for k in parts]
             + sorted(k for k in info if k.startswith("table:")))
    for k in order:
        if k in info:
            x, y, w, h = N[k]
            A(f'<rect class="af-hit" data-card="{esc(k)}" x="{x}" y="{y}" width="{w}" height="{h}" rx="6" tabindex="0" '
              f'role="button" aria-label="{esc(info[k]["t"])}: what it is"/>')
    for e in edges:
        if e["n"]:
            sx, sy = E[e["id"]]["step"]
            A(f'<g class="af-mark" data-s="{e["n"]}" tabindex="0" role="button" aria-label="Step {e["n"]}">'
              f'<circle class="af-step" cx="{sx}" cy="{sy}" r="12"/><text class="af-sn" x="{sx}" y="{sy + 4.5}">{e["n"]}</text></g>')

    def mk(i, c, sz=8):
        return (f'<marker id="af-{i}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="{sz}" markerHeight="{sz}" '
                f'orient="auto"><path class="{c}" d="M0,0 L10,5 L0,10 z"/></marker>')

    defs = "<defs>" + mk("a", "af-ma") + mk("g", "af-mg") + mk("b", "af-mb") + mk("c", "af-mc", 7) + "</defs>"
    svg = (f'<svg class="appflow" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {lay["width"]} {lay["height"]}" role="img" '
           f'aria-label="The application, inside: one request followed through every service it reaches">' + defs + "".join(s) + "</svg>")
    bar = ('<div class="af-bar"><button type="button" id="af-play">Follow one request</button>'
           '<button type="button" id="af-prev" aria-label="Previous step">&lsaquo;</button>'
           '<button type="button" id="af-next" aria-label="Next step">&rsaquo;</button>'
           '<button type="button" id="af-all">Show all</button>'
           '<span class="af-caption" id="af-caption" aria-live="polite">Point at a step to see its arrow. Select a box to see what it is.</span></div>'
           '<div class="af-live" id="af-live"><span class="af-live-say" id="af-live-say">No environment is up: the picture shows the design.</span>'
           '<span class="seg" id="af-live-env" hidden></span></div>')
    ol = "<ol class=\"appflow-steps\">" + "".join(f'<li data-s="{n}">{t}</li>' for n, (_, t) in enumerate(steps, 1)) + "</ol>"
    tail = (f'<p class="sub">A service that is down loses nothing: its events wait in the queue. An event that fails '
            f'{max_receive} times moves to its dead-letter queue' + (", where an alarm waits." if alarm_silent else ".") + "</p>")
    # THE PICTURE DURING A CYCLE (2026-10-06): which reading in a status file
    # belongs to which box - a service's `status_key` from the manifest, a
    # queue's key from the observation script that writes it - and where each
    # box is, so the page can put the live counts on them. No new data: the
    # page already reads these files for the estate.
    observed = dict((q, k) for k, q in re.findall(r'^(\w+)="\$\(observe_queue (\w+)\)"', OBSERVE.read_text(), re.M))
    queues_drawn = sorted({e["src"].split(":", 1)[1] for e in edges if e["kind"] == "failp"})
    unobserved = [q for q in queues_drawn if q not in observed]
    if unobserved:
        raise Refusal(f"{OBSERVE.name} observes no queue named {unobserved} - the picture could not show it live")
    live = {"services": {f"service:{sv['name']}": sv["status_key"] for sv in services if sv.get("status_key")},
            "queues": {f"queue:{q}": observed[q] for q in queues_drawn}}
    live["boxes"] = {k: N[k] for k in list(live["services"]) + list(live["queues"]) + ["dlq"]}
    data = json.dumps({"steps": groups, "edges": [[e["id"], e["src"], e["dst"]] for e in edges], "cards": info, "live": live},
                      separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
    return ('<!-- GENERATED by scripts/generate-app-flow.py from services.json, infra/modules/queue and the code it cites, '
            'placed by assets/app-flow-layout.json. Do not edit. -->\n'
            f'{bar}\n<div class="appflow-wrap">{svg}</div>\n<div class="af-card" id="af-card" hidden></div>\n{ol}\n{tail}\n'
            f'<script type="application/json" id="af-data">{data}</script>\n')


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
    print(f"app-flow: wrote {OUT.relative_to(ROOT)} - {out.count('<li data-s=')} steps, {len(out.encode()):,} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
