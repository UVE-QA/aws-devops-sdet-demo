#!/usr/bin/env python3
"""What size the per-cycle environment actually is, read from the configuration.

A price is a price; a SHAPE is a property of this repository. Fargate is billed
per vCPU-hour and per GB-hour, RDS per instance-hour for a named class and per
GB-month of storage — so a cost estimate needs both, and only one of them comes
from AWS.

WHY THIS IS DERIVED AND NOT WRITTEN DOWN
----------------------------------------
`generate-topology.py` made the argument already and it applies here without a
change: a number written beside the thing it describes is the sixth stale place
waiting to happen. "0.25 vCPU, 512 MiB" in a rate table would keep saying 0.25
long after somebody raised `task_cpu`, and the cost estimate would be wrong in a
direction nobody could see. So the shape is read out of `infra/` every time the
fold runs, and no file records it — there is nothing to go stale, which is
stronger than checking a recorded copy against the configuration. What
`make rates-check` verifies is that the read still SUCCEEDS for every per-cycle
level, because a shape the fold cannot resolve is a cost it cannot compute.

WHAT MAKES THIS SOUND, AND THE REFUSAL THAT PROTECTS IT
-------------------------------------------------------
Reading variable DEFAULTS is only the effective configuration while nothing
overrides them. Today nothing does: no `*.tfvars` file is committed, no workflow
passes `-var` or `-var-file` for any sizing knob, and the only `TF_VAR_*` in the
workflows are app_image, owner, budget_email, launch_id, expires_at and
demo_account_id. That is a fact about the repository as it stands, not a
guarantee — so this module REFUSES when it finds a `.tfvars` in an environment
directory rather than quietly reading defaults that something else is
overriding.

Usage:
    from sizing import environment_shape
    shape = environment_shape(Path("infra/envs/stage"))
"""

from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
RDS_MODULE = ROOT / "infra/modules/rds"

# A variable block's default, for the simple scalar case that is all this
# repository uses. Anything cleverer would be a terraform parser, and a half of
# one is worse than none.
_VARIABLE = re.compile(
    r'variable\s+"(?P<name>[A-Za-z0-9_]+)"\s*\{(?P<body>.*?)\n\}',
    re.DOTALL,
)
_DEFAULT = re.compile(r'^\s*default\s*=\s*(?P<value>.+?)\s*$', re.MULTILINE)
_MODULE_ARG = re.compile(r'^\s*(?P<name>[A-Za-z0-9_]+)\s*=\s*(?P<value>.+?)\s*$', re.MULTILINE)


class Refusal(Exception):
    """Something the configuration does not let this module answer honestly."""


def _scalar(text: str):
    text = text.strip().strip('"')
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        return text


def variable_defaults(directory: pathlib.Path) -> dict:
    """Every `variable "x" { default = ... }` in one directory, as a dict."""
    found: dict = {}
    for path in sorted(directory.glob("*.tf")):
        text = path.read_text(encoding="utf-8")
        for match in _VARIABLE.finditer(text):
            default = _DEFAULT.search(match.group("body"))
            if default:
                found[match.group("name")] = _scalar(default.group("value"))
    return found


def _module_block(directory: pathlib.Path, name: str) -> str | None:
    for path in sorted(directory.glob("*.tf")):
        text = path.read_text(encoding="utf-8")
        marker = f'module "{name}" {{'
        start = text.find(marker)
        if start == -1:
            continue
        depth = 0
        for index in range(start + len(marker) - 1, len(text)):
            if text[index] == "{":
                depth += 1
            elif text[index] == "}":
                depth -= 1
                if depth == 0:
                    return text[start + len(marker):index]
    return None


def environment_shape(env_dir: pathlib.Path) -> dict:
    """The billable shape of one per-cycle environment.

    Raises Refusal when the configuration cannot answer, which includes the case
    where something outside it might be answering instead.
    """
    env_dir = env_dir.resolve()
    if not env_dir.is_dir():
        raise Refusal(f"{env_dir}: no such environment directory")

    try:
        shown = env_dir.relative_to(ROOT)
    except ValueError:
        shown = env_dir

    overrides = sorted(p.name for p in env_dir.glob("*.tfvars"))
    if overrides:
        raise Refusal(
            f"{shown}: {', '.join(overrides)} present — variable defaults are no "
            "longer the effective configuration, so the shape cannot be read from them"
        )

    defaults = variable_defaults(env_dir)
    missing = [k for k in ("task_cpu", "task_memory", "desired_count", "db_instance_class")
               if k not in defaults]
    if missing:
        raise Refusal(f"{shown}: no default for {', '.join(missing)}")

    # allocated_storage lives in the module unless the environment overrides it.
    storage = None
    rds_call = _module_block(env_dir, "rds")
    if rds_call is None:
        raise Refusal(f"{shown}: no module \"rds\" block")
    for arg in _MODULE_ARG.finditer(rds_call):
        if arg.group("name") == "allocated_storage":
            storage = _scalar(arg.group("value"))
    storage_from = str(env_dir.relative_to(ROOT)) if storage is not None else None
    if storage is None:
        module_defaults = variable_defaults(RDS_MODULE)
        if "allocated_storage" not in module_defaults:
            raise Refusal(f"{RDS_MODULE}: no default for allocated_storage")
        storage = module_defaults["allocated_storage"]
        storage_from = str(RDS_MODULE.relative_to(ROOT))

    for key in ("task_cpu", "task_memory", "desired_count"):
        if not isinstance(defaults[key], int):
            raise Refusal(f"{shown}: {key} is not a plain number ({defaults[key]!r})")

    return {
        "task_vcpu": defaults["task_cpu"] / 1024.0,
        "task_gb": defaults["task_memory"] / 1024.0,
        "task_count": defaults["desired_count"],
        "db_instance_class": defaults["db_instance_class"],
        "db_allocated_gb": storage,
        "from": {
            "task_cpu": f"{env_dir.relative_to(ROOT)}/variables.tf",
            "task_memory": f"{env_dir.relative_to(ROOT)}/variables.tf",
            "desired_count": f"{env_dir.relative_to(ROOT)}/variables.tf",
            "db_instance_class": f"{env_dir.relative_to(ROOT)}/variables.tf",
            "db_allocated_gb": storage_from,
        },
    }


if __name__ == "__main__":  # pragma: no cover - a convenience, not an interface
    import json
    import sys

    target = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "infra/envs/stage"
    try:
        print(json.dumps(environment_shape(target), indent=2))
    except Refusal as exc:
        print(f"refused: {exc}", file=sys.stderr)
        raise SystemExit(2)
