#!/usr/bin/env python3
"""The estate as a schema (plan item 5, ADR-0099): the graph the board's second
layout draws, GENERATED from what the repository already declares.

    site/data/schema.json

One graph per environment. Its NODES are the board's own nouns - the same ids
as site/data/topology.json, so the page's states, colours and figures are the
board's and not a second opinion - plus a finer grain inside the runtime,
PARTS: the tasks of an ECS service, the nodes and pods of the lab's cluster,
the two queues under the one tile, the target groups behind a balancer. Its
EDGES come from three places and nowhere else:

    the modules' inputs     `module "api" { target_group_arn = module.alb.… }`
                            is an edge api -> alb, named by the argument;
                            a policy at the environment level whose role is
                            one module's and whose resource another's is an
                            edge named by the policy
    the chart               `helm template` over charts/demo: an Ingress path
                            to a Service, a Service selector to a Deployment,
                            a ServiceAccount to the IRSA role its annotation
                            names - the lab's inside, which Terraform never sees
    the observation         not edges but COUNTS: each part names the path in
                            status/<env>.json it is coloured from, running
                            against desired, ready against desired

Nothing here is drawn by hand. An edge without a source line is a refusal; a
part without an observation path is a refusal; a node the topology does not
draw is a refusal. Layout is lanes - network, edge, runtime, data, ops - and
an order within each, as numbers the page turns into pixels; the page never
decides what connects to what.

    python3 scripts/generate-schema.py            # write site/data/schema.json
    python3 scripts/generate-schema.py --check    # refuse on drift

Needs helm for the chart's half, as chart-check does.
"""
from __future__ import annotations

import json
import pathlib
import re
import shutil
import subprocess
import sys
from collections import Counter, defaultdict

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
TOPOLOGY = ROOT / "site/data/topology.json"
GROUPS = ROOT / "assets/topology-groups.json"
OUT = ROOT / "site/data/schema.json"
CHART = ROOT / "charts/demo"

LANES = ["network", "edge", "runtime", "data", "ops"]
LANE_OF = {
    "vpc": "network",
    "alb": "edge",
    "ecs_api": "runtime", "ecs_web": "runtime", "ecs_worker": "runtime",
    "eks": "runtime", "k8s_api": "runtime", "k8s_worker": "runtime",
    "rds": "data", "secrets": "data", "queue": "data",
    "cloudwatch": "ops", "budgets": "ops", "dnsrec": "ops",
}
# THE LAYERS THE VISITOR SWITCHES (ADR-0099 D4, redrawn 2026-09-14 after the
# owner saw the first picture): a concern each, never an object. `traffic`
# is where a request goes - the balancer's rule to the tasks, the Ingress to
# the Service to the pods; `data` is who reads and writes which store;
# `identity` the policies and the IRSA roles; `network` the wiring Terraform
# passes between modules - VPC, subnets, security groups, the target group's
# registration, the DNS alias; `ops` the log groups. The first two are on by
# default; the VPC itself is drawn as the box everything sits in, not as a
# tile with eleven arrows into it.
LAYERS = [
    {"id": "traffic", "on": True, "what": "the balancer's rule to the tasks; the Ingress to the Service to the pods"},
    {"id": "data", "on": True, "what": "who reads the database and the secret, who publishes to and consumes from each queue"},
    {"id": "identity", "on": False, "what": "the IAM policies and the IRSA roles"},
    {"id": "network", "on": False, "what": "VPC, subnets, security groups, the target group's registration, the DNS alias"},
    {"id": "ops", "on": False, "what": "the log groups"},
]
# A noun on a layer is hidden with it; the rest are always drawn. Only the
# lab's two IRSA-role groups qualify - they are identity and nothing else.
NOUN_LAYER = {"k8s_api": "identity", "k8s_worker": "identity"}
# Where the page puts a part: inside its parent's tile, in the edge column
# (an Ingress, with its Services inside), on the cluster's label line, or in
# the cluster's box.
PLACE_OF_PART = {"ingress": "edge", "service": "edge", "control-plane": "label", "nodes": "label",
                 "pods": "cluster", "hook": "cluster"}
LAYER_OF_ARG = [
    (re.compile(r"queue_arn$"), "identity"),  # what the eks module writes IRSA policies from
    (re.compile(r"vpc|subnet|security_group|target_group|dns|zone|^name$|^zone_id$"), "network"),
    (re.compile(r"secret|queue|db_|_url$", re.I), "data"),
    (re.compile(r"log_group"), "ops"),
]
# `{ name = "ITEMS_QUEUE_URL", value = module.queue.queue_url }` - the
# environment a service is given, one object per line.
ENV_ITEM = re.compile(r'\{\s*name\s*=\s*"([A-Za-z_]+)"\s*,\s*value\s*=\s*(.+?)\s*\}')
# What the page reads a part's numbers from, in status/<env>.json.
ECS_SERVICES = {
    "ecs_api": ("api", "resources.ecs_service"),
    "ecs_web": ("web", "resources.ecs_web_service"),
    "ecs_worker": ("worker", "resources.ecs_worker_service"),
}
CHART_PLACEHOLDERS = [
    "--set", "images.api.repository=r", "--set", "images.api.digest=sha256:a",
    "--set", "images.web.repository=r", "--set", "images.web.digest=sha256:b",
    "--set", "images.worker.repository=r", "--set", "images.worker.digest=sha256:c",
    "--set", "itemsQueueUrl=https://sqs.example/q", "--set", "resultsQueueUrl=https://sqs.example/r",
    "--set", "serviceAccounts.api.roleArn=arn:aws:iam::0:role/api-irsa",
    "--set", "serviceAccounts.worker.roleArn=arn:aws:iam::0:role/worker-irsa",
]


class Refusal(Exception):
    pass


def read_json(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- terraform
MODULE_BLOCK = re.compile(r'^module\s+"([^"]+)"\s*\{', re.M)
RESOURCE_BLOCK = re.compile(r'^(resource|data)\s+"([^"]+)"\s+"([^"]+)"\s*\{', re.M)
MODULE_REF = re.compile(r'\bmodule\.([a-z_]+)\.([a-z_]+)')
ARG = re.compile(r'^\s*([a-z_]+)\s*=\s*(.+?)\s*$', re.M)
HELM_SET = re.compile(r'set\s*\{\s*name\s*=\s*"([^"]+)"\s*value\s*=\s*(.+?)\s*\}', re.S)


def blocks(text: str):
    """Every top-level block as (kind, name, body, line) with its braces balanced."""
    out = []
    for m in list(MODULE_BLOCK.finditer(text)) + list(RESOURCE_BLOCK.finditer(text)):
        start = m.end() - 1
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    body = text[start + 1:i]
                    break
        else:
            raise Refusal(f"unbalanced block at {m.group(0)!r}")
        line = text.count("\n", 0, m.start()) + 1
        if m.re is MODULE_BLOCK:
            out.append(("module", m.group(1), body, line))
        else:
            out.append((m.group(1) + ":" + m.group(2), m.group(3), body, line))
    return out


def env_calls(level: pathlib.Path) -> dict[str, str]:
    """module call name -> module source directory (relative to infra/)."""
    calls = {}
    for tf in sorted(level.glob("*.tf")):
        for kind, name, body, _ in blocks(tf.read_text(encoding="utf-8")):
            if kind != "module":
                continue
            src = re.search(r'source\s*=\s*"([^"]+)"', body)
            if src:
                calls[name] = str((level / src.group(1)).resolve().relative_to(ROOT))
    return calls


def call_groups(env: str, level: pathlib.Path, assign: dict) -> dict[str, str]:
    """module call name -> the display group most of its blocks belong to."""
    out = {}
    for call, src in env_calls(level).items():
        key = f"{src}@{call}"
        table = assign.get(key) or assign.get(src) or {}
        if not table:
            continue
        top = Counter(table.values()).most_common(1)[0][0]
        out[call] = top
    return out


def terraform_edges(env: str, level: pathlib.Path, groups: dict[str, str], shown: set[str],
                    env_assign: dict[str, str]) -> list[dict]:
    """The environment level's edges: a module's inputs that name another
    module, a resource of the level (assigned to a group by the topology,
    like prod's Route 53 record) whose arguments name a module, and a policy
    whose role is one module's and whose document names another."""
    edges = []
    for tf in sorted(level.glob("*.tf")):
        text = tf.read_text(encoding="utf-8")
        rel = str(tf.relative_to(ROOT))
        docs = {}  # data.aws_iam_policy_document.NAME -> set of referenced module calls
        for kind, name, body, line in blocks(text):
            if kind == "data:aws_iam_policy_document":
                docs[name] = sorted({m.group(1) for m in MODULE_REF.finditer(body)})
        for kind, name, body, line in blocks(text):
            if kind == "module":
                here = groups.get(name)
                if not here or here not in shown:
                    continue
                args = [(m.group(1), m.group(2)) for m in ARG.finditer(body)]
                args += [(m.group(1), m.group(2)) for m in ENV_ITEM.finditer(body)]
                for via, expr in args:
                    for ref in MODULE_REF.finditer(expr):
                        there = groups.get(ref.group(1))
                        if not there or there not in shown or there == here:
                            continue
                        edges.append({"from": f"{env}.{here}", "to": f"{env}.{there}",
                                      "via": via, "kind": "input",
                                      "source": f"{rel}:{line}"})
            elif kind.startswith("resource:") and kind != "resource:aws_iam_role_policy":
                here = env_assign.get(f"{kind.split(':', 1)[1]}.{name}")
                if not here or here not in shown:
                    continue
                # A Helm value is named by its `set { name = … }`, not by the
                # word `value`: the controller's `vpcId` is the edge.
                args = [(m.group(1), m.group(2)) for m in HELM_SET.finditer(body)]
                args += [(m.group(1), m.group(2)) for m in ARG.finditer(body) if m.group(1) != "value"]
                for via, expr in args:
                    for ref in MODULE_REF.finditer(expr):
                        there = groups.get(ref.group(1))
                        if not there or there not in shown or there == here:
                            continue
                        edges.append({"from": f"{env}.{here}", "to": f"{env}.{there}",
                                      "via": via, "kind": "input",
                                      "source": f"{rel}:{line}"})
            elif kind == "resource:aws_iam_role_policy":
                role = re.search(r'role\s*=\s*module\.([a-z_]+)\.', body)
                doc = re.search(r'policy\s*=\s*data\.aws_iam_policy_document\.([a-z_]+)\.json', body)
                if not role or not doc:
                    continue
                here = groups.get(role.group(1))
                for call in docs.get(doc.group(1), []):
                    there = groups.get(call)
                    if not here or not there or there == here or here not in shown or there not in shown:
                        continue
                    edges.append({"from": f"{env}.{here}", "to": f"{env}.{there}",
                                  "via": name, "kind": "policy", "source": f"{rel}:{line}"})
    # one edge per (from, to, via)
    seen = set()
    unique = []
    for e in edges:
        key = (e["from"], e["to"], e["via"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(e)
    return unique


def alb_paths() -> list[tuple[str, str]]:
    """The listener rule's paths and where they go, from the ALB module."""
    text = (ROOT / "infra/modules/alb/main.tf").read_text(encoding="utf-8")
    rule = re.search(r'resource "aws_lb_listener_rule" "api" \{(.*?)\n\}', text, re.S)
    if not rule:
        raise Refusal("infra/modules/alb/main.tf has no listener rule `api`")
    values = re.search(r'values\s*=\s*\[([^\]]+)\]', rule.group(1))
    paths = [v.strip().strip('"') for v in values.group(1).split(",")] if values else []
    return [(", ".join(paths), "api"), ("everything else", "web")]


def irsa_edges(env: str) -> list[dict]:
    """The lab's policies live in the eks module, on the IRSA roles: each
    `aws_iam_role_policy` whose document names var.queue_arn or
    var.results_queue_arn is an edge from that role's group to that queue."""
    text = (ROOT / "infra/modules/eks/irsa.tf").read_text(encoding="utf-8")
    role_group = {"api": "k8s_api", "worker": "k8s_worker", "controller": "eks"}
    docs = {}
    for kind, name, body, _ in blocks(text):
        if kind == "data:aws_iam_policy_document":
            docs[name] = body
    edges = []
    for kind, name, body, line in blocks(text):
        if kind != "resource:aws_iam_role_policy":
            continue
        role = re.search(r'role\s*=\s*aws_iam_role\.([a-z_]+)\.name', body)
        doc = re.search(r'policy\s*=\s*data\.aws_iam_policy_document\.([a-z_]+)\.json', body)
        if not role or not doc or role.group(1) not in role_group:
            continue
        for var, queue in (("var.queue_arn", "items"), ("var.results_queue_arn", "results")):
            if var in docs.get(doc.group(1), ""):
                edges.append({"from": f"{env}.{role_group[role.group(1)]}", "to": f"{env}.queue.{queue}",
                              "via": name, "kind": "policy", "source": f"infra/modules/eks/irsa.tf:{line}"})
    return edges


# ---------------------------------------------------------------- the chart
def rendered_chart() -> list[dict]:
    if not shutil.which("helm"):
        raise Refusal("helm is not on PATH; the chart's half of the schema cannot be read")
    result = subprocess.run(["helm", "template", "demo", str(CHART), *CHART_PLACEHOLDERS],
                            capture_output=True, text=True)
    if result.returncode != 0:
        raise Refusal("helm template failed:\n" + result.stderr[-800:])
    return [d for d in yaml.safe_load_all(result.stdout) if d]


def chart_parts(env: str, cluster: str, irsa_group: dict[str, str]) -> tuple[list[dict], list[dict]]:
    """Parts and edges inside the cluster, from the rendered chart."""
    docs = rendered_chart()
    parts, edges = [], []
    by_kind = defaultdict(list)
    for d in docs:
        by_kind[d["kind"]].append(d)
    deployments = {d["metadata"]["name"]: d for d in by_kind["Deployment"]}
    sa_role = {}
    for sa in by_kind["ServiceAccount"]:
        arn = (sa["metadata"].get("annotations") or {}).get("eks.amazonaws.com/role-arn", "")
        sa_role[sa["metadata"]["name"]] = arn.rsplit("/", 1)[-1]
    for name, d in deployments.items():
        spec = d["spec"]["template"]["spec"]
        container = spec["containers"][0]
        ports = [p.get("containerPort") for p in container.get("ports", [])]
        pid = f"{env}.{cluster}.pods_{name}"
        parts.append({"id": pid, "parent": f"{env}.{cluster}", "kind": "pods", "label": f"pods · {name}",
                      "port": ports[0] if ports else None,
                      "observe": {"path": f"resources.eks.deployments[name={name}]", "have": "ready", "want": "desired"},
                      "source": f"charts/demo/templates/{name}.yaml"})
        sa = spec.get("serviceAccountName")
        if sa and sa_role.get(sa):
            suffix = sa_role[sa].split("-lab-", 1)[-1] if "-lab-" in sa_role[sa] else sa_role[sa]
            group = irsa_group.get(suffix)
            if group:
                edges.append({"from": pid, "to": f"{env}.{group}", "via": f"serviceAccount {sa} → IRSA",
                              "kind": "identity", "source": "charts/demo/templates/serviceaccounts.yaml"})
        for envvar in container.get("env", []):
            ref = (envvar.get("valueFrom") or {}).get("secretKeyRef")
            if ref:
                edges.append({"from": pid, "to": f"{env}.secrets",
                              "via": f"{envvar.get('name')} from Secret {ref['name']}, filled from Secrets Manager",
                              "kind": "data", "source": f"charts/demo/templates/{name}.yaml"})
                # THE POD THAT HOLDS DATABASE_URL IS THE POD THAT TALKS TO THE
                # DATABASE (the owner, 2026-09-14: in the lab it was not clear
                # who does). The cluster's security group is what RDS admits -
                # every node, so every pod - and that edge stays on the network
                # layer; this one says which Deployments actually connect.
                if envvar.get("name") == "DATABASE_URL":
                    edges.append({"from": pid, "to": f"{env}.rds",
                                  "via": f"DATABASE_URL - connects to the database with the credentials in Secret {ref['name']}",
                                  "kind": "data", "source": f"charts/demo/templates/{name}.yaml"})
            if envvar.get("name") == "ITEMS_QUEUE_URL":
                edges.append({"from": pid, "to": f"{env}.queue.items", "via": "ITEMS_QUEUE_URL",
                              "kind": "data", "source": f"charts/demo/templates/{name}.yaml"})
            if envvar.get("name") == "RESULTS_QUEUE_URL":
                edges.append({"from": pid, "to": f"{env}.queue.results", "via": "RESULTS_QUEUE_URL",
                              "kind": "data", "source": f"charts/demo/templates/{name}.yaml"})
    for svc in by_kind["Service"]:
        name = svc["metadata"]["name"]
        selector = svc["spec"].get("selector", {})
        target = selector.get("app.kubernetes.io/name")
        sid = f"{env}.{cluster}.svc_{name}"
        parts.append({"id": sid, "parent": f"{env}.{cluster}", "kind": "service", "label": f"Service · {name}",
                      "port": (svc["spec"].get("ports") or [{}])[0].get("port"), "observe": None,
                      "source": f"charts/demo/templates/{name}.yaml"})
        if target in deployments:
            edges.append({"from": sid, "to": f"{env}.{cluster}.pods_{target}", "via": "selector",
                          "kind": "network", "source": f"charts/demo/templates/{name}.yaml"})
    for ing in by_kind["Ingress"]:
        iid = f"{env}.{cluster}.ingress"
        parts.append({"id": iid, "parent": f"{env}.{cluster}", "kind": "ingress", "label": "Ingress → ALB",
                      "observe": {"path": "resources.load_balancer", "have": "state", "want": None},
                      "source": "charts/demo/templates/ingress.yaml"})
        for rule in ing["spec"].get("rules", []):
            for p in rule.get("http", {}).get("paths", []):
                svc = p["backend"]["service"]["name"]
                edges.append({"from": iid, "to": f"{env}.{cluster}.svc_{svc}", "via": p["path"],
                              "kind": "network", "source": "charts/demo/templates/ingress.yaml"})
    for job in by_kind["Job"]:
        name = job["metadata"]["name"].replace("demo-", "")
        parts.append({"id": f"{env}.{cluster}.hook_{name}", "parent": f"{env}.{cluster}", "kind": "hook",
                      "label": f"hook · {name}", "observe": None, "source": "charts/demo/templates/hooks.yaml"})
    return parts, edges


def edge_layer(e: dict) -> str:
    if e["kind"] in ("policy", "identity"):
        return "identity"
    if e["kind"] == "network":
        return "traffic"  # the listener rule to the tasks, the Ingress paths, the Service selectors
    if e["kind"] == "data":
        return "data"
    for pattern, layer in LAYER_OF_ARG:
        if pattern.search(e["via"]):
            return layer
    raise Refusal(f"edge {e['from']} -> {e['to']} via {e['via']!r}: no layer for that argument; add a rule to LAYER_OF_ARG")


# ---------------------------------------------------------------- the graph
def build() -> dict:
    topology = read_json(TOPOLOGY)
    spec = read_json(GROUPS)
    shown = {g["id"] for g in spec["groups"] if g.get("shown")}
    assign = spec["assign"]
    out = {"schema": "schema/1", "lanes": LANES, "layers": LAYERS, "environments": {}}
    irsa_group = {"api-irsa": "k8s_api", "worker-irsa": "k8s_worker"}
    for env in topology["estate"]["environments"]:
        eid = env["id"]
        level = ROOT / env["level"]
        groups = call_groups(eid, level, assign)
        nouns = []
        for n in env["nodes"]:
            gid = n["id"].split(".", 1)[1]
            lane = LANE_OF.get(gid)
            if lane is None:
                raise Refusal(f"{n['id']}: no lane for group {gid!r}; add it to LANE_OF")
            nouns.append({"id": n["id"], "group": gid, "label": n["label"], "service": n["service"],
                          "lane": lane, "layer": NOUN_LAYER.get(gid), "resources": n.get("resources")})
        order = {lane: 0 for lane in LANES}
        for n in nouns:
            n["col"] = order[n["lane"]]
            order[n["lane"]] += 1
        parts, edges = [], terraform_edges(eid, level, groups, shown, assign.get(env["level"], {}))
        runtime = "eks" if any(n["group"] == "eks" for n in nouns) else "ecs"
        # the queues under the one tile, wherever the tile is
        if any(n["group"] == "queue" for n in nouns):
            for q, path in (("items", "resources.queue"), ("results", "resources.results_queue")):
                parts.append({"id": f"{eid}.queue.{q}", "parent": f"{eid}.queue", "kind": "queue",
                              "label": f"{q} + dlq",
                              "observe": {"path": path, "have": "visible", "want": None, "alarm": "dead_letter_alarm"},
                              "source": f"infra/modules/queue (module \"{'queue' if q == 'items' else 'results'}\")"})
        if runtime == "ecs":
            for gid, (svc, path) in ECS_SERVICES.items():
                if any(n["group"] == gid for n in nouns):
                    parts.append({"id": f"{eid}.{gid}.tasks", "parent": f"{eid}.{gid}", "kind": "tasks",
                                  "label": f"tasks · {svc}",
                                  "observe": {"path": path, "have": "running", "want": "desired"},
                                  "source": "infra/modules/ecs-service/main.tf"})
            if any(n["group"] == "alb" for n in nouns):
                for paths, target in alb_paths():
                    pid = f"{eid}.alb.tg_{target}"
                    parts.append({"id": pid, "parent": f"{eid}.alb", "kind": "target-group",
                                  "label": f"{paths} → {target}", "observe": None,
                                  "source": "infra/modules/alb/main.tf"})
                    edges.append({"from": pid, "to": f"{eid}.ecs_{target}.tasks", "via": "targets",
                                  "kind": "network", "source": "infra/modules/alb/main.tf"})
            # the policies and the URLs name the queue tile; the parts say which queue
            for e in list(edges):
                if e["to"].endswith(".queue") and (e["kind"] == "policy" or e["via"].endswith("_QUEUE_URL")):
                    which = "results" if "results" in e["via"].lower() else "items"
                    e["to"] = f"{eid}.queue.{which}"
        else:
            parts.append({"id": f"{eid}.eks.control_plane", "parent": f"{eid}.eks", "kind": "control-plane",
                          "label": "control plane", "observe": {"path": "resources.eks.cluster", "have": "status", "want": None},
                          "source": "infra/modules/eks/main.tf"})
            variables = (ROOT / "infra/modules/eks/variables.tf").read_text(encoding="utf-8")
            capacity = re.search(r'variable "capacity_type".*?default\s*=\s*"([A-Z_]+)"', variables, re.S)
            parts.append({"id": f"{eid}.eks.nodes", "parent": f"{eid}.eks", "kind": "nodes",
                          "label": "nodes" + (f" · {capacity.group(1).lower()}" if capacity else ""),
                          "observe": {"path": "resources.eks.node_group", "have": None, "want": "desired"},
                          "source": "infra/modules/eks/main.tf"})
            cparts, cedges = chart_parts(eid, "eks", irsa_group)
            parts += cparts
            edges += cedges
            edges += irsa_edges(eid)
            for e in list(edges):
                if e["kind"] == "policy" and e["to"].endswith(".queue"):
                    which = "results" if "results" in e["via"] else "items"
                    e["to"] = f"{eid}.queue.{which}"
        ids = {n["id"] for n in nouns} | {p["id"] for p in parts}
        # WHO TALKS TO THE DATABASE, said as such (the owner, 2026-09-14: "не
        # совсем понятно кто и как общается с РДС"). The rds module ADMITS a
        # security group - that input is the database saying who may connect,
        # and it is drawn from the client to the database, on the data layer,
        # as the connection it permits. And the secret the rds module made is
        # read from Secrets Manager, so the credentials edge points at that
        # tile and not at the database.
        has_secrets = any(n["group"] == "secrets" for n in nouns)
        for e in edges:
            if (e["via"] in ("ecs_app_security_group_id", "extra_client_security_group_ids") and e["from"].endswith(".rds")
                    and not e["to"].endswith(".eks")):  # the cluster's group is every node's; its pods say who connects
                e["from"], e["to"] = e["to"], e["from"]
                e["via"] = f"connects - its security group is admitted by RDS ({e['via']})"
                e["kind"] = "data"
            elif e["via"] == "db_secret_arn" and has_secrets:
                e["to"] = f"{eid}.secrets"
                e["via"] = "db_secret_arn - reads the database credentials"
        for p in parts:
            p["place"] = PLACE_OF_PART.get(p["kind"], "inside")
        for e in edges:
            e["layer"] = edge_layer(e)
        for e in edges:
            for end in ("from", "to"):
                if e[end] not in ids:
                    raise Refusal(f"{eid}: edge {e['from']} -> {e['to']} ({e['via']}) names {e[end]}, which nothing draws")
            if not e.get("source"):
                raise Refusal(f"{eid}: edge {e['from']} -> {e['to']} has no source")
        for p in parts:
            if p["parent"] not in ids:
                raise Refusal(f"{eid}: part {p['id']} hangs off {p['parent']}, which nothing draws")
        out["environments"][eid] = {"runtime": runtime, "nouns": nouns, "parts": parts, "edges": edges,
                                    "counts": {"nouns": len(nouns), "parts": len(parts), "edges": len(edges)}}
    out["_"] = ("GENERATED by scripts/generate-schema.py from site/data/topology.json, the modules' inputs in "
                "infra/envs/*, the listener rule in infra/modules/alb and `helm template` over charts/demo "
                "(ADR-0099). Do not edit; `make schema` regenerates it and `make schema-check` refuses drift.")
    return out


def main(argv: list[str]) -> int:
    check = "--check" in argv
    try:
        graph = build()
    except Refusal as exc:
        print(f"schema: REFUSED\n{exc}", file=sys.stderr)
        return 2
    text = json.dumps(graph, indent=2, ensure_ascii=True) + "\n"
    if check:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != text:
            print("schema: DRIFT\nsite/data/schema.json disagrees with infra/, charts/ or the topology. "
                  "Run `make schema` and commit the result.", file=sys.stderr)
            return 2
        print("schema: clean - " + ", ".join(
            f"{e}: {v['counts']['nouns']} nouns, {v['counts']['parts']} parts, {v['counts']['edges']} edges"
            for e, v in graph["environments"].items()))
        return 0
    OUT.write_text(text, encoding="utf-8")
    print("schema: wrote site/data/schema.json - " + ", ".join(
        f"{e} ({v['runtime']}): {v['counts']['nouns']} nouns, {v['counts']['parts']} parts, {v['counts']['edges']} edges"
        for e, v in graph["environments"].items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
