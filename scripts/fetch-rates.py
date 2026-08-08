#!/usr/bin/env python3
"""Capture a dated rate table from AWS's own price list. Never type a price.

    scripts/fetch-rates.py        -> site/data/rates.json

WHY A CAPTURE AND NOT A TABLE SOMEBODY WROTE
--------------------------------------------
`docs/cost-control.md` already committed to this in its second paragraph: costs
are written "from measured runs and the Terraform defaults, not from a price list
assumed rather than checked". A price typed from memory is the same class of
object as a hand-written resource inventory — it looks like a fact, it is a
recollection, and nothing around it changes when it goes stale. So the table is
captured from the AWS Price List Query API, carries the date it was captured and
the exact filters that produced each figure, and is committed as evidence.

IT REFUSES RATHER THAN PICKS
----------------------------
A filter that matches two products, or a product whose OnDemand terms carry two
different prices, means the query did not identify one thing — and choosing the
first would produce a plausible number with nothing behind it. Every such case
is a refusal that PRINTS what it saw, including the distinct usagetypes, because
the fix is always to narrow the filter and the only hard part is knowing what
AWS calls the thing. Budget one failed run for a new price; that is cheaper than
a wrong one that never announces itself.

WHAT IS NOT HERE
----------------
No shape and no judgement. The task size and the storage size are read from
`infra/` by scripts/sizing.py; which kinds are worth metering at all is editorial
and lives in assets/cost-model.json. This file only asks AWS what things cost.

Needs credentials (pricing:GetProducts, a free read-only API) and runs in
us-east-1, where the price list endpoint lives, whatever region is being priced.

Usage:
    scripts/fetch-rates.py [--region us-west-2] [--out site/data/rates.json]
"""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from sizing import Refusal, environment_shape  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "site/data/rates.json"
SCHEMA = "rates/1"

# The price list encodes the region in `usagetype` with its own abbreviation, and
# there is no rule that derives it. One entry, for the one region this project
# deploys to; anything else is a refusal rather than a guess (ADR-0045 D3).
USAGE_PREFIX = {"us-west-2": "USW2"}

# Every query, declared. `{prefix}` is the abbreviation above; `{db_class}` is
# read from the configuration, so the instance being priced is the instance the
# repository actually declares.
QUERIES = {
    "alb_hour": {
        "service": "AWSELB",
        "filters": {
            "regionCode": "{region}",
            "productFamily": "Load Balancer-Application",
            "usagetype": "{prefix}-LoadBalancerUsage",
        },
    },
    "fargate_vcpu_hour": {
        "service": "AmazonECS",
        "filters": {
            "regionCode": "{region}",
            "usagetype": "{prefix}-Fargate-vCPU-Hours:perCPU",
        },
    },
    "fargate_gb_hour": {
        "service": "AmazonECS",
        "filters": {
            "regionCode": "{region}",
            "usagetype": "{prefix}-Fargate-GB-Hours",
        },
    },
    "rds_instance_hour": {
        "service": "AmazonRDS",
        "filters": {
            "regionCode": "{region}",
            "instanceType": "{db_class}",
            "databaseEngine": "PostgreSQL",
            "deploymentOption": "Single-AZ",
            "licenseModel": "No license required",
        },
    },
    "rds_gp3_gb_month": {
        "service": "AmazonRDS",
        "filters": {
            "regionCode": "{region}",
            "productFamily": "Database Storage",
            "usagetype": "{prefix}-RDS:GP3-Storage",
        },
    },
}


class Refused(Exception):
    pass


def get_products(service: str, filters: dict) -> list[dict]:
    argv = [
        "aws", "pricing", "get-products",
        "--region", "us-east-1",
        "--service-code", service,
        "--output", "json",
        "--filters",
    ]
    for field, value in filters.items():
        argv.append(f"Type=TERM_MATCH,Field={field},Value={value}")
    result = subprocess.run(argv, capture_output=True, text=True)
    if result.returncode != 0:
        raise Refused(f"{service}: aws pricing get-products failed\n{result.stderr.strip()}")
    payload = json.loads(result.stdout or "{}")
    return [json.loads(item) for item in payload.get("PriceList", [])]


def one_price(key: str, service: str, filters: dict) -> dict:
    products = get_products(service, filters)
    if not products:
        raise Refused(f"{key}: no product matched {filters}")

    seen: dict[tuple, dict] = {}
    usagetypes = set()
    for product in products:
        usagetypes.add(product.get("product", {}).get("attributes", {}).get("usagetype", "?"))
        sku = product.get("product", {}).get("sku")
        for term in (product.get("terms", {}).get("OnDemand") or {}).values():
            for dimension in (term.get("priceDimensions") or {}).values():
                usd = dimension.get("pricePerUnit", {}).get("USD")
                if usd is None:
                    continue
                value = float(usd)
                if value == 0.0:
                    # A zero dimension is a free-tier line, not this rate.
                    continue
                seen[(value, dimension.get("unit"))] = {
                    "usd": value,
                    "unit": dimension.get("unit"),
                    "sku": sku,
                    "description": dimension.get("description"),
                }

    if not seen:
        raise Refused(
            f"{key}: {len(products)} product(s) matched and none carried a non-zero "
            f"OnDemand price. usagetypes seen: {sorted(usagetypes)}"
        )
    if len(seen) > 1:
        rendered = ", ".join(f"{v['usd']} per {v['unit']}" for v in seen.values())
        raise Refused(
            f"{key}: the filter did not identify one price — {len(seen)} distinct: "
            f"{rendered}. usagetypes seen: {sorted(usagetypes)}. Narrow the filter."
        )

    price = next(iter(seen.values()))
    price["filters"] = filters
    price["service_code"] = service
    return price


def db_classes() -> list[str]:
    """Every distinct RDS class the per-cycle levels declare, from infra/."""
    classes = []
    for env_dir in sorted((ROOT / "infra/envs").iterdir()):
        if not env_dir.is_dir():
            continue
        shape = environment_shape(env_dir)
        if shape["db_instance_class"] not in classes:
            classes.append(shape["db_instance_class"])
    return classes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", default="us-west-2")
    parser.add_argument("--out", type=pathlib.Path, default=OUT)
    args = parser.parse_args()

    prefix = USAGE_PREFIX.get(args.region)
    if not prefix:
        print(f"refused: no usagetype abbreviation recorded for {args.region}. "
              f"Add it to USAGE_PREFIX rather than letting this guess.", file=sys.stderr)
        return 2

    try:
        classes = db_classes()
    except Refusal as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    if len(classes) != 1:
        print(f"refused: the per-cycle levels declare {len(classes)} RDS classes "
              f"({', '.join(classes)}); this table prices one.", file=sys.stderr)
        return 2

    substitutions = {"region": args.region, "prefix": prefix, "db_class": classes[0]}
    unit_prices: dict[str, dict] = {}
    failures: list[str] = []
    for key, query in QUERIES.items():
        filters = {f: v.format(**substitutions) for f, v in query["filters"].items()}
        try:
            unit_prices[key] = one_price(key, query["service"], filters)
        except Refused as exc:
            failures.append(str(exc))

    if failures:
        for failure in failures:
            print(f"refused: {failure}", file=sys.stderr)
        print(f"\n{len(failures)} of {len(QUERIES)} prices could not be identified; "
              f"nothing written.", file=sys.stderr)
        return 2

    table = {
        "_comment": (
            "CAPTURED from the AWS Price List Query API by scripts/fetch-rates.py. Not "
            "generated from this repository and not edited by hand: every figure carries "
            "the SKU and the exact filters that produced it, and `captured_at` is when. "
            "Regenerate with `make rates`, which needs AWS credentials."
        ),
        "schema": SCHEMA,
        "region": args.region,
        "currency": "USD",
        "captured_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "AWS Price List Query API (pricing:GetProducts, endpoint us-east-1)",
        "priced_for": {"db_instance_class": classes[0]},
        "unit_prices": dict(sorted(unit_prices.items())),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(table, indent=2) + "\n", encoding="utf-8")

    print(f"rates: {len(unit_prices)} unit prices captured for {args.region} "
          f"-> {args.out.relative_to(ROOT) if args.out.is_absolute() else args.out}")
    width = max(len(k) for k in unit_prices)
    for key, price in sorted(unit_prices.items()):
        print(f"  {key.ljust(width)}  {price['usd']:>12.8f} per {price['unit']}  {price['sku']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
