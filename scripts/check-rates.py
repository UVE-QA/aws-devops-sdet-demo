#!/usr/bin/env python3
"""Every kind the configuration declares is priced, free, or named — never zero by silence.

`make rates-check`. It reads the resource kinds out of `infra/envs/*` the same way
`generate-topology.py` reads resource blocks out of `infra/`, and refuses when one
of them appears in none of assets/cost-model.json's three buckets.

THE CLAIM UNDER GATE
--------------------
A cost estimate can be wrong in two ways. It can multiply badly — that is
`make cost-check`. Or it can silently leave something out, which is worse,
because the number still looks like an answer. A NAT gateway added to the network
module would cost real money every hour and would contribute exactly nothing to
an estimate that had never heard of it, and nothing about the output would look
different.

So the rule is coverage, and it is checked against the configuration rather than
against a list somebody maintains beside it: this is ADR-0041's second discovery
channel — read what the repository DECLARES, not what an index happens to know —
pointed at money instead of at leftovers.

It also refuses the other direction. A bucket entry for a kind no level declares
any more is stale, and a stale exemption is how something re-enters the
configuration already excused.

Needs no credentials and makes no AWS call: two files and infra/.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from sizing import Refusal, environment_shape  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
MODEL = ROOT / "assets/cost-model.json"
RATES = ROOT / "site/data/rates.json"
ENVS = ROOT / "infra/envs"


def topology_module():
    spec = importlib.util.spec_from_file_location(
        "generate_topology", ROOT / "scripts/generate-topology.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def declared_kinds() -> dict[str, list[str]]:
    """Every resource TYPE the per-cycle levels declare, and where."""
    gt = topology_module()
    kinds: dict[str, list[str]] = {}
    for env_dir in sorted(p for p in ENVS.iterdir() if p.is_dir()):
        for address, _decl_dir, _decl in gt.expand(env_dir):
            kind = address.split(".")[-2]
            kinds.setdefault(kind, [])
            name = env_dir.name
            if name not in kinds[kind]:
                kinds[kind].append(name)
    return kinds


def main() -> int:
    findings: list[str] = []

    try:
        model = json.loads(MODEL.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"rates: REFUSED — {MODEL.relative_to(ROOT)} is missing", file=sys.stderr)
        return 1

    buckets = {name: set(model.get(name, {})) for name in ("priced", "free", "not_metered")}
    classified = set().union(*buckets.values())

    kinds = declared_kinds()
    for kind, envs in sorted(kinds.items()):
        homes = [name for name, members in buckets.items() if kind in members]
        if not homes:
            findings.append(
                f"unclassified kind: {kind} is declared in {', '.join(envs)} and is in "
                f"none of priced/free/not_metered — a silent zero")
        elif len(homes) > 1:
            findings.append(f"{kind} is in {len(homes)} buckets at once: {', '.join(homes)}")

    for stale in sorted(classified - set(kinds)):
        where = [name for name, members in buckets.items() if stale in members]
        findings.append(
            f"stale entry: {stale} is listed under {', '.join(where)} and no per-cycle "
            f"level declares it")

    # Every price the model reaches for has to exist in the captured table.
    try:
        rates = json.loads(RATES.read_text(encoding="utf-8"))
    except FileNotFoundError:
        rates = None
        findings.append(
            f"no rate table: {RATES.relative_to(ROOT)} is missing. Capture it with "
            f"`make rates` — the estimate cannot be computed from a price nobody fetched")

    if rates is not None:
        unit_prices = set(rates.get("unit_prices", {}))
        for kind, spec in sorted(model.get("priced", {}).items()):
            for component in spec.get("components", []):
                if component["unit_price"] not in unit_prices:
                    findings.append(
                        f"{kind} is priced by '{component['unit_price']}', which the rate "
                        f"table does not carry")
        for key, price in sorted(rates.get("unit_prices", {}).items()):
            for field in ("usd", "unit", "sku", "filters"):
                if not price.get(field) and price.get(field) != 0:
                    findings.append(f"unit price '{key}' has no {field} — provenance is the point")

    # The shape has to be readable, or the fold has nothing to multiply.
    for env_dir in sorted(p for p in ENVS.iterdir() if p.is_dir()):
        try:
            environment_shape(env_dir)
        except Refusal as exc:
            findings.append(f"shape: {exc}")

    if findings:
        print(f"rates: {len(findings)} finding(s)", file=sys.stderr)
        for finding in findings:
            print(f"  - {finding}", file=sys.stderr)
        return 1

    counts = {name: len(members) for name, members in buckets.items()}
    line = (f"rates: clean — {len(kinds)} kinds declared across "
            f"{len([p for p in ENVS.iterdir() if p.is_dir()])} per-cycle levels; "
            f"{counts['priced']} priced, {counts['free']} free, "
            f"{counts['not_metered']} named but not metered")
    if rates is not None:
        captured = rates.get("captured_at")
        age = ""
        try:
            when = datetime.strptime(captured, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            age = f", {(datetime.now(timezone.utc) - when).days} days old"
        except (TypeError, ValueError):
            age = ", captured_at unreadable"
        # Age is REPORTED and never fails the gate: a check that reddens with the
        # passage of time reddens a build nobody changed, and the project's rule is
        # that a gate fires on a defect, not on a calendar.
        line += f"\nrates: table captured {captured} for {rates.get('region')}{age}"
    print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
