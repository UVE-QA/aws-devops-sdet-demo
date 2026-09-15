#!/usr/bin/env python3
"""manifest-check: services.json against every copy of it (ADR-0101).

The three services are declared in seven places that never met, and this is
the comparison. It reads the manifest and then each copy, and refuses on the
first disagreement it finds in each - it does not stop at the first, so one
run names everything that drifted.

Both directions. A service in the manifest must be in every copy, with the
same image, context, port, health, routes, queues and database; and a
service any copy declares must be in the manifest - the ecs-service modules
of stage and prod, the compose services that build, the chart's `images.*`
keys and Deployment templates, the build steps of the two workflows, the
repositories scripts/lab-install.sh resolves, the keys observe-environment.sh
writes a service's reading under. scripts/generate-schema.py is not a copy
any more: it reads this file (slice 6b). Add a service in one place and forget the
manifest, and this is red; add it to the manifest and forget one copy, and
this is red. That is the whole point: the copies stay hand-written in this
slice, and the file is the one place they must agree with.

Text, not parsers. The copies are Terraform, YAML and a Makefile, and this
gate runs on python3 with nothing installed (assets/gates.json: local). The
files are read as the shapes they actually have - a top-level block per
module, two-space indentation per compose service, `key: value` per chart
line - and the reader that misreads one would refuse loudly rather than pass
quietly, because everything it reads is compared with something.

Usage: python3 scripts/check-manifest.py [--root DIR]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

ENVS_ECS = ("stage", "prod")
WORKFLOWS_BUILDING = ("self-service.yml", "deploy-stage.yml")
WORKFLOWS_NAMING = ("promote-prod.yml",)
QUEUE_MODULE = {"items": "queue", "results": "results"}


def fail(findings: list[str], text: str) -> None:
    findings.append(text)


# ----------------------------------------------------------------- readers --

def tf_blocks(text: str, kind: str) -> dict[str, str]:
    """Top-level `kind "name" {` blocks, closed by a `}` at column 0."""
    out = {}
    for m in re.finditer(rf'^{kind} "([^"]+)" \{{\n(.*?)^\}}', text, re.S | re.M):
        out[m.group(1)] = m.group(2)
    return out


def tf_resources(text: str) -> dict[str, str]:
    """Top-level `resource "type" "name" {` blocks, keyed `type.name`."""
    out = {}
    for m in re.finditer(r'^resource "([^"]+)" "([^"]+)" \{\n(.*?)^\}', text, re.S | re.M):
        out[f"{m.group(1)}.{m.group(2)}"] = m.group(3)
    return out


def tf_arg(block: str, name: str) -> str | None:
    m = re.search(rf'^\s*{re.escape(name)}\s*=\s*(.+?)\s*$', block, re.M)
    return m.group(1) if m else None


def tf_variable_default(text: str, name: str) -> str | None:
    block = tf_blocks(text, "variable").get(name)
    if block is None:
        return None
    raw = tf_arg(block, "default")
    return raw.strip('"') if raw is not None else None


def compose_services(text: str) -> dict[str, str]:
    """`services:` children at two spaces, each with its indented body."""
    m = re.search(r'^services:\n(.*?)(?=^\S|\Z)', text, re.S | re.M)
    body = m.group(1) if m else ""
    out = {}
    for sm in re.finditer(r'^  (\w[\w-]*):\n(.*?)(?=^  \w|\Z)', body, re.S | re.M):
        out[sm.group(1)] = sm.group(2)
    return out


def yaml_scalar(block: str, key: str) -> str | None:
    m = re.search(rf'^\s*{re.escape(key)}:\s*(.+?)\s*$', block, re.M)
    return m.group(1).strip('"\'') if m else None


def yaml_children(text: str, key: str, indent: int) -> list[str]:
    """The keys nested one level under `key:` at the given indentation."""
    pad = " " * indent
    m = re.search(rf'^{pad}{re.escape(key)}:\n((?:{pad}  .*\n|\s*\n|{pad}  *#.*\n)*)', text, re.M)
    if not m:
        return []
    return re.findall(rf'^{pad}  (\w[\w-]*):', m.group(1), re.M)


# ------------------------------------------------------------------ checks --

def check_manifest_shape(manifest: dict, findings: list[str]) -> list[dict]:
    if manifest.get("schema") != 1:
        fail(findings, "services.json: schema is not 1")
    services = manifest.get("services") or []
    if not services:
        fail(findings, "services.json: no services declared")
    names = [s.get("name") for s in services]
    if len(set(names)) != len(names):
        fail(findings, f"services.json: a name repeats: {names}")
    required = ("name", "image", "context", "compose", "status_key", "port", "health", "routes", "queues", "database", "suites")
    for s in services:
        for k in required:
            if k not in s:
                fail(findings, f"services.json: {s.get('name')!r} lacks `{k}`")
        if s.get("port") is None and s.get("routes"):
            fail(findings, f"services.json: {s['name']} has routes and no port")
        if "default" in (s.get("routes") or []) and len(s["routes"]) != 1:
            fail(findings, f"services.json: {s['name']} is the default route and has other routes too")
        for q in (s.get("queues") or {}).get("publishes", []) + (s.get("queues") or {}).get("consumes", []):
            if q not in QUEUE_MODULE:
                fail(findings, f"services.json: {s['name']} names a queue this project has no module for: {q}")
    return services


def check_dockerfiles(root: pathlib.Path, services: list[dict], findings: list[str]) -> None:
    for s in services:
        df = root / s["context"] / "Dockerfile"
        if not df.exists():
            fail(findings, f"{s['name']}: no Dockerfile at {df.relative_to(root)}")
            continue
        exposed = re.findall(r'^EXPOSE\s+(\d+)', df.read_text(), re.M)
        if s["port"] is None and exposed:
            fail(findings, f"{s['name']}: the manifest says no port, {df.relative_to(root)} EXPOSEs {exposed}")
        if s["port"] is not None and str(s["port"]) not in exposed:
            fail(findings, f"{s['name']}: port {s['port']} in the manifest, {df.relative_to(root)} EXPOSEs {exposed or 'nothing'}")


def check_compose(root: pathlib.Path, services: list[dict], findings: list[str]) -> None:
    text = (root / "docker-compose.yml").read_text()
    blocks = compose_services(text)
    by_compose = {s["compose"]: s for s in services}
    for name, body in blocks.items():
        if "build:" not in body:
            continue
        s = by_compose.get(name)
        if s is None:
            fail(findings, f"docker-compose.yml builds `{name}`, which services.json does not declare")
            continue
        image = yaml_scalar(body, "image")
        if image != f"{s['image']}:local":
            fail(findings, f"docker-compose.yml: {name} is image `{image}`, the manifest says `{s['image']}:local`")
        context = yaml_scalar(body, "context")
        if context not in (f"./{s['context']}", s["context"]):
            fail(findings, f"docker-compose.yml: {name} builds from `{context}`, the manifest says `./{s['context']}`")
        if not s["health"].startswith("/") and s["health"] not in body:
            fail(findings, f"docker-compose.yml: {name}'s healthcheck does not run `{s['health']}`")
        if s["port"] is not None and s["routes"] == ["default"]:
            if not re.search(rf':{s["port"]}"', body):
                fail(findings, f"docker-compose.yml: {name} is the one published service and does not publish container port {s['port']}")
    for s in services:
        if s["compose"] not in blocks:
            fail(findings, f"docker-compose.yml has no service `{s['compose']}` for {s['name']}")


def check_terraform(root: pathlib.Path, services: list[dict], findings: list[str]) -> None:
    for env in ENVS_ECS:
        env_dir = root / "infra" / "envs" / env
        main = (env_dir / "main.tf").read_text()
        variables = (env_dir / "variables.tf").read_text()
        modules = tf_blocks(main, "module")
        ecs_modules = {n: b for n, b in modules.items() if (tf_arg(b, "source") or "").strip('"').endswith("/ecs-service")}
        for n, b in ecs_modules.items():
            if n not in {s["name"] for s in services}:
                fail(findings, f"infra/envs/{env}: module \"{n}\" is an ecs-service that services.json does not declare")
        queue_names = {}
        for n, b in modules.items():
            if (tf_arg(b, "source") or "").strip('"').endswith("/queue"):
                queue_names[n] = (tf_arg(b, "name") or '"items"').strip('"')
        for q, mod in QUEUE_MODULE.items():
            if queue_names.get(mod) != q:
                fail(findings, f"infra/envs/{env}: expected module \"{mod}\" to be the `{q}` queue, found {queue_names}")
        for s in services:
            b = ecs_modules.get(s["name"])
            if b is None:
                fail(findings, f"infra/envs/{env}: no ecs-service module \"{s['name']}\"")
                continue
            where = f"infra/envs/{env} module \"{s['name']}\""
            if (tf_arg(b, "service") or "").strip('"') != s["name"]:
                fail(findings, f"{where}: service = {tf_arg(b, 'service')}, not \"{s['name']}\"")
            image_var = (tf_arg(b, "image") or "").removeprefix("var.")
            default = tf_variable_default(variables, image_var)
            if default != f"{s['image']}:bootstrap":
                fail(findings, f"{where}: image = var.{image_var} whose default is `{default}`, the manifest's repository is `{s['image']}`")
            port_var = tf_arg(b, "port")
            if s["port"] is None:
                if port_var is not None:
                    fail(findings, f"{where}: has a port, the manifest says none")
            else:
                pdefault = tf_variable_default(variables, (port_var or "").removeprefix("var."))
                if pdefault != str(s["port"]):
                    fail(findings, f"{where}: port = {port_var} (default {pdefault}), the manifest says {s['port']}")
            health = tf_arg(b, "health_check_command") or ""
            if s["health"] not in health.replace("${var." + (port_var or "").removeprefix("var.") + "}", str(s["port"])):
                fail(findings, f"{where}: health_check_command does not check `{s['health']}`")
            has_secret = tf_arg(b, "db_secret_arn") is not None
            if has_secret != (s["database"] is not None):
                fail(findings, f"{where}: db_secret_arn is {'set' if has_secret else 'absent'}, the manifest says the service {'owns' if s['database'] else 'has no'} database")
            env_names = set(re.findall(r'name = "([A-Z_]+)"', b))
            wants = {f"{q.upper()}_QUEUE_URL" for q in s["queues"]["publishes"] + s["queues"]["consumes"]}
            if wants != env_names:
                fail(findings, f"{where}: queue URLs in extra_environment are {sorted(env_names)}, the manifest wants {sorted(wants)}")
            has_tg = tf_arg(b, "target_group_arn") is not None
            if has_tg != bool(s["routes"]):
                fail(findings, f"{where}: {'has' if has_tg else 'has no'} target group, the manifest says routes {s['routes']}")
        # The queues' IAM: a policy per direction, named after the service.
        for s in services:
            for q in s["queues"]["publishes"]:
                if f'"{s["name"]}_publish_{q}"' not in main:
                    fail(findings, f"infra/envs/{env}: no policy {s['name']}_publish_{q} for a queue the manifest says {s['name']} publishes")
            for q in s["queues"]["consumes"]:
                if f'"{s["name"]}_consume_{q}"' not in main:
                    fail(findings, f"infra/envs/{env}: no policy {s['name']}_consume_{q} for a queue the manifest says {s['name']} consumes")


def check_alb(root: pathlib.Path, services: list[dict], findings: list[str]) -> None:
    text = (root / "infra" / "modules" / "alb" / "main.tf").read_text()
    resources = tf_resources(text)
    routed = [s for s in services if s["routes"] and s["routes"] != ["default"]]
    default = [s for s in services if s["routes"] == ["default"]]
    if len(default) != 1:
        fail(findings, f"services.json: exactly one service takes the default route, found {[s['name'] for s in default]}")
    for s in routed:
        rule = resources.get(f"aws_lb_listener_rule.{s['name']}")
        if rule is None:
            fail(findings, f"infra/modules/alb: no aws_lb_listener_rule \"{s['name']}\" for routes {s['routes']}")
            continue
        m = re.search(r'path_pattern \{\s*values = \[([^\]]*)\]', rule)
        values = re.findall(r'"([^"]+)"', m.group(1)) if m else []
        if values != s["routes"]:
            fail(findings, f"infra/modules/alb: rule \"{s['name']}\" forwards {values}, the manifest says {s['routes']}")
    for key in resources:
        if key.startswith("aws_lb_listener_rule.") and key.split(".", 1)[1] not in {s["name"] for s in routed}:
            fail(findings, f"infra/modules/alb: listener rule `{key}` routes to a service the manifest gives no routes")
    # The target groups keep their historical names: `app` is the api's, from
    # the days of one container.
    tg_of = {"api": "app"}
    for s in services:
        if s["port"] is None or not s["routes"]:
            continue
        tg = resources.get(f"aws_lb_target_group.{tg_of.get(s['name'], s['name'])}")
        if tg is None:
            fail(findings, f"infra/modules/alb: no target group for {s['name']}")
        elif f'path                = "{s["health"]}"' not in tg and f'path = "{s["health"]}"' not in tg:
            fail(findings, f"infra/modules/alb: {s['name']}'s target group does not check `{s['health']}`")
    for key in resources:
        if key.startswith("aws_lb_target_group."):
            name = key.split(".", 1)[1]
            if name not in {tg_of.get(s["name"], s["name"]) for s in services if s["routes"]}:
                fail(findings, f"infra/modules/alb: target group `{name}` belongs to no service in services.json")


def check_chart(root: pathlib.Path, services: list[dict], findings: list[str]) -> None:
    chart = root / "charts" / "demo"
    values = (chart / "values.yaml").read_text()
    image_keys = yaml_children(values, "images", 0)
    names = {s["name"] for s in services}
    for k in image_keys:
        if k not in names:
            fail(findings, f"charts/demo/values.yaml: images.{k} is a service services.json does not declare")
    for s in services:
        if s["name"] not in image_keys:
            fail(findings, f"charts/demo/values.yaml: no images.{s['name']}")
        tpl = chart / "templates" / f"{s['name']}.yaml"
        if not tpl.exists():
            fail(findings, f"charts/demo/templates: no {s['name']}.yaml")
            continue
        body = tpl.read_text()
        if f'"name" "{s["name"]}"' not in body:
            fail(findings, f"charts/demo/templates/{s['name']}.yaml: does not take images.{s['name']}")
        ports = re.findall(r'containerPort:\s*(\d+)', body)
        if s["port"] is None and ports:
            fail(findings, f"charts/demo/templates/{s['name']}.yaml: containerPort {ports}, the manifest says no port")
        if s["port"] is not None and str(s["port"]) not in ports:
            fail(findings, f"charts/demo/templates/{s['name']}.yaml: containerPort {ports or 'absent'}, the manifest says {s['port']}")
        if s["health"].startswith("/"):
            paths = set(re.findall(r'^\s*path:\s*(\S+)', body, re.M))
            if paths != {s["health"]}:
                fail(findings, f"charts/demo/templates/{s['name']}.yaml: probes {sorted(paths)}, the manifest says {s['health']}")
        elif s["health"] not in body:
            fail(findings, f"charts/demo/templates/{s['name']}.yaml: no probe runs `{s['health']}`")
        for var in [f"{q.upper()}_QUEUE_URL" for q in s["queues"]["publishes"] + s["queues"]["consumes"]]:
            if var not in body:
                fail(findings, f"charts/demo/templates/{s['name']}.yaml: does not receive {var}")
        if (s["database"] is not None) != ("DATABASE_URL" in body):
            fail(findings, f"charts/demo/templates/{s['name']}.yaml: DATABASE_URL {'present' if 'DATABASE_URL' in body else 'absent'}, the manifest says {'a' if s['database'] else 'no'} database")
    for tpl in (chart / "templates").glob("*.yaml"):
        m = re.search(r'kind:\s*Deployment', tpl.read_text())
        if m and tpl.stem not in names:
            fail(findings, f"charts/demo/templates/{tpl.name}: a Deployment for a service services.json does not declare")
    ingress = (chart / "templates" / "ingress.yaml").read_text()
    found = re.findall(r'- path:\s*(\S+)\s*\n\s*pathType:\s*(\w+)\s*\n\s*backend:\s*\n\s*service:\s*\n\s*name:\s*(\w+)', ingress)
    want = []
    for s in services:
        for r in s["routes"]:
            if r == "default":
                want.append(("/", "Prefix", s["name"]))
            elif r.endswith("/*"):
                want.append((r[:-2], "Prefix", s["name"]))
            else:
                want.append((r, "Exact", s["name"]))
    if sorted(found) != sorted(want):
        fail(findings, f"charts/demo/templates/ingress.yaml: paths {sorted(found)}, the manifest's routes give {sorted(want)}")


def check_workflows(root: pathlib.Path, services: list[dict], findings: list[str]) -> None:
    """Since ADR-0101 D6 a workflow names a service and nothing else about it:
    a build step runs `scripts/build-service.sh <name>`, the image variables
    of an apply are `TF_VAR_<name>_image`, and the repositories and digests
    come from scripts/service-images.sh. A repository name spelled in a
    workflow is a copy that came back."""
    names = {s["name"] for s in services}
    for wf in WORKFLOWS_BUILDING + WORKFLOWS_NAMING:
        text = (root / ".github" / "workflows" / wf).read_text()
        for s in services:
            if s["image"] in text:
                fail(findings, f".github/workflows/{wf}: spells the repository {s['image']} - the manifest is the one copy (scripts/service-images.sh)")
            if f"TF_VAR_{s['name']}_image:" not in text:
                fail(findings, f".github/workflows/{wf}: no TF_VAR_{s['name']}_image for {s['name']}")
        for m in re.finditer(r'TF_VAR_([a-z_]+)_image:', text):
            if m.group(1) not in names:
                fail(findings, f".github/workflows/{wf}: TF_VAR_{m.group(1)}_image is a service services.json does not declare")
        if "scripts/service-images.sh" not in text:
            fail(findings, f".github/workflows/{wf}: resolves no image through scripts/service-images.sh")
    for wf in WORKFLOWS_BUILDING:
        text = (root / ".github" / "workflows" / wf).read_text()
        built = re.findall(r'build-service\.sh\s+(\S+)', text)
        for name in built:
            if name not in names:
                fail(findings, f".github/workflows/{wf}: builds `{name}`, which services.json does not declare")
        for s in services:
            if s["name"] not in built:
                fail(findings, f".github/workflows/{wf}: no build step for {s['name']}")
            elif f"- name: Build, tag, and push the {s['name']} image" not in text:
                fail(findings, f".github/workflows/{wf}: the build step for {s['name']} is not named the way the page lights it")


def check_lab_install(root: pathlib.Path, services: list[dict], findings: list[str]) -> None:
    text = (root / "scripts" / "lab-install.sh").read_text()
    if "scripts/service-images.sh tag" not in text:
        fail(findings, "scripts/lab-install.sh: does not resolve its digests through scripts/service-images.sh")
    for s in services:
        if s["image"] in text:
            fail(findings, f"scripts/lab-install.sh: spells the repository {s['image']} - the manifest is the one copy")


def check_page_bindings(root: pathlib.Path, services: list[dict], findings: list[str]) -> None:
    """The page lights an `ECR push` node by the name of the step that builds
    the service (assets/topology-groups.json, `live`); one node per service."""
    spec = json.loads((root / "assets" / "topology-groups.json").read_text())
    nodes = {}
    for phase in spec.get("phases", []):
        for n in phase.get("nodes", []):
            if n.get("id", "").startswith("build."):
                nodes[n["id"].split(".", 1)[1]] = n
    names = {s["name"] for s in services}
    for name in nodes:
        if name not in names:
            fail(findings, f"assets/topology-groups.json: node build.{name} builds a service services.json does not declare")
    for s in services:
        n = nodes.get(s["name"])
        if n is None:
            fail(findings, f"assets/topology-groups.json: no build.{s['name']} node for the page to light when {s['name']} is built")
            continue
        want = f"Build, tag, and push the {s['name']} image"
        for live in n.get("live", []):
            if want not in live.get("steps", []):
                fail(findings, f"assets/topology-groups.json: build.{s['name']} is lit by {live.get('steps')} in {live.get('workflow')}, not by `{want}`")


def check_observation(root: pathlib.Path, services: list[dict], findings: list[str]) -> None:
    """status/<env>.json is written by observe-environment.sh, and the page and
    the schema read a service's tasks from `resources.<status_key>`."""
    text = (root / "scripts" / "observe-environment.sh").read_text()
    written = set(re.findall(r'^\s+(ecs_\w+):\s*\$', text, re.M))
    for s in services:
        if s["status_key"] not in written:
            fail(findings, f"scripts/observe-environment.sh never writes resources.{s['status_key']}, where the manifest says {s['name']}'s tasks are read from")
    for key in written:
        if key not in {s["status_key"] for s in services}:
            fail(findings, f"scripts/observe-environment.sh writes resources.{key}, a service reading services.json does not declare")


def check_database_and_suites(root: pathlib.Path, services: list[dict], findings: list[str]) -> None:
    makefile = (root / "Makefile").read_text()
    targets = set(re.findall(r'^([a-z][\w-]*):', makefile, re.M))
    for s in services:
        for t in s["suites"]:
            if t not in targets:
                fail(findings, f"{s['name']}: suite `{t}` is not a Makefile target")
        db = s["database"]
        if db is None:
            continue
        mig = root / db["migrations"]
        if not (mig / "env.py").exists():
            fail(findings, f"{s['name']}: no alembic env at {db['migrations']}")
            continue
        env = (mig / "env.py").read_text()
        m = re.search(r'^SCHEMA = "(\w+)"', env, re.M)
        schema = m.group(1) if m else "public"
        if schema != db["schema"]:
            fail(findings, f"{s['name']}: migrations at {db['migrations']} own schema `{schema}`, the manifest says `{db['schema']}`")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=pathlib.Path(__file__).resolve().parent.parent)
    args = ap.parse_args()
    root = pathlib.Path(args.root)
    findings: list[str] = []
    manifest = json.loads((root / "services.json").read_text())
    services = check_manifest_shape(manifest, findings)
    if findings:
        for f in findings:
            print(f"manifest-check: {f}")
        return 1
    for check in (check_dockerfiles, check_compose, check_terraform, check_alb, check_chart,
                  check_workflows, check_lab_install, check_page_bindings, check_observation, check_database_and_suites):
        check(root, services, findings)
    if findings:
        for f in findings:
            print(f"manifest-check: {f}")
        print(f"manifest-check: {len(findings)} disagreement(s) between services.json and its copies")
        return 1
    copies = 2 + len(ENVS_ECS) + 1 + 1 + len(WORKFLOWS_BUILDING) + len(WORKFLOWS_NAMING) + 2
    print(f"manifest-check: {len(services)} services agree across {copies} copies: "
          + ", ".join(s["name"] for s in services))
    return 0


if __name__ == "__main__":
    sys.exit(main())
