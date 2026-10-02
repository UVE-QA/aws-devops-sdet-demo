#!/usr/bin/env python3
"""Who looked at the dashboard: unique visitors, page views and rough places,
from CloudFront's access logs (2026-10-02).

    python3 scripts/visitors.py [--days 7] [--html report.html]
    make visitors [DAYS=7]

Reads the logs bucket of infra/public-site (aws-devops-sdet-demo-site-logs-
<account>), syncing it into a local cache first so a second run downloads only
what is new. Needs credentials that may read that bucket - demo-admin here.

What counts, and why:
- A PAGE VIEW is a GET of `/` or `/index.html` answered 200 or 304. An open
  page asks the bucket for its status documents once a minute; those are
  requests, not visits, and are not counted.
- A VISITOR is one IP address with one browser, per day for the daily rows and
  over the whole period for the total. Two people behind one office address
  with the same browser count once; one person on a phone and a laptop counts
  twice. It is an estimate and says so.
- Not counted: crawlers and link previews (by their user agent), and headless
  Chrome - which is this repository's own tooling, the page checks and the
  screenshots taken from the devbox. Add addresses to leave out, one per line,
  in ~/.config/aws-devops-sdet-demo/visitors-exclude.
- WHERE is CloudFront's edge location: the city of the point of presence that
  answered, which is near the visitor and not the visitor. The distribution is
  PriceClass_100 - North America, Europe, Israel - so a visitor from Asia or
  South America is answered from the nearest of those and appears there.
- FROM is the referrer's site: the link someone followed, or `direct`. A
  visitor is counted once under every source they came through.

Nothing printed or written by this script contains an IP address.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import gzip
import html
import json
import os
import pathlib
import re
import subprocess
import sys
import urllib.parse

CACHE = pathlib.Path(os.environ.get("VISITORS_CACHE", pathlib.Path.home() / ".cache/aws-devops-sdet-demo/cf-logs"))
EXCLUDE_FILE = pathlib.Path.home() / ".config/aws-devops-sdet-demo/visitors-exclude"
PAGES = {"/", "/index.html"}
NOT_PEOPLE = re.compile(r"bot|crawl|spider|slurp|preview|facebookexternalhit|embedly|monitor|uptime|curl|wget|"
                        r"python-|go-http|okhttp|java/|headlesschrome|lighthouse|pingdom|scan", re.I)

# The edge's first three letters are an airport code. The ones CloudFront runs
# in the regions of PriceClass_100; an unknown code is printed as it is.
EDGES = {
    "IAD": "Ashburn, US", "ATL": "Atlanta, US", "BOS": "Boston, US", "ORD": "Chicago, US", "CMH": "Columbus, US",
    "DFW": "Dallas, US", "DEN": "Denver, US", "DTW": "Detroit, US", "IAH": "Houston, US", "JAX": "Jacksonville, US",
    "MCI": "Kansas City, US", "LAX": "Los Angeles, US", "MIA": "Miami, US", "MSP": "Minneapolis, US",
    "BNA": "Nashville, US", "EWR": "Newark, US", "JFK": "New York, US", "PHL": "Philadelphia, US",
    "PHX": "Phoenix, US", "PDX": "Portland, US", "HIO": "Hillsboro, US", "SLC": "Salt Lake City, US",
    "SFO": "San Francisco, US", "SJC": "San Jose, US", "SEA": "Seattle, US", "STL": "St. Louis, US",
    "TPA": "Tampa, US", "OKC": "Oklahoma City, US", "LAS": "Las Vegas, US", "CLT": "Charlotte, US",
    "YUL": "Montreal, CA", "YTO": "Toronto, CA", "YYZ": "Toronto, CA", "YVR": "Vancouver, CA", "YYC": "Calgary, CA",
    "QRO": "Querétaro, MX", "MEX": "Mexico City, MX",
    "AMS": "Amsterdam, NL", "ATH": "Athens, GR", "TXL": "Berlin, DE", "BER": "Berlin, DE", "BRU": "Brussels, BE",
    "OTP": "Bucharest, RO", "BUD": "Budapest, HU", "CPH": "Copenhagen, DK", "DUB": "Dublin, IE",
    "DUS": "Düsseldorf, DE", "FRA": "Frankfurt, DE", "HAM": "Hamburg, DE", "HEL": "Helsinki, FI",
    "LIS": "Lisbon, PT", "LHR": "London, GB", "MAN": "Manchester, GB", "MAD": "Madrid, ES", "BCN": "Barcelona, ES",
    "MRS": "Marseille, FR", "CDG": "Paris, FR", "MXP": "Milan, IT", "FCO": "Rome, IT", "PMO": "Palermo, IT",
    "MUC": "Munich, DE", "OSL": "Oslo, NO", "PRG": "Prague, CZ", "SOF": "Sofia, BG", "ARN": "Stockholm, SE",
    "VIE": "Vienna, AT", "WAW": "Warsaw, PL", "ZAG": "Zagreb, HR", "ZRH": "Zurich, CH", "TLV": "Tel Aviv, IL",
}


def bucket() -> str:
    if os.environ.get("VISITORS_BUCKET"):
        return os.environ["VISITORS_BUCKET"]
    acct = subprocess.run(["aws", "sts", "get-caller-identity", "--query", "Account", "--output", "text"],
                          capture_output=True, text=True)
    if acct.returncode != 0:
        sys.exit("visitors: no AWS credentials - sign in to SSO first (demo-admin)\n" + acct.stderr.strip()[-300:])
    return f"aws-devops-sdet-demo-site-logs-{acct.stdout.strip()}"


def sync(b: str) -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["aws", "s3", "sync", f"s3://{b}/cloudfront/", str(CACHE), "--only-show-errors"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"visitors: could not read s3://{b}/cloudfront/\n{r.stderr.strip()[-400:]}")


def excluded() -> set[str]:
    if not EXCLUDE_FILE.is_file():
        return set()
    return {ln.strip() for ln in EXCLUDE_FILE.read_text().splitlines() if ln.strip() and not ln.startswith("#")}


def where(edge: str) -> str:
    return EDGES.get(edge[:3].upper(), edge[:3].upper() or "?")


def came_from(ref: str) -> str:
    if ref in ("-", ""):
        return "direct"
    host = urllib.parse.urlparse(urllib.parse.unquote(ref)).hostname or "?"
    host = host.removeprefix("www.")
    if host in ("demo.uveapp.net", "uveapp.net"):
        return "this site"
    if "linkedin" in host or host == "lnkd.in":
        return "linkedin"
    if host.startswith("google.") or ".google." in host:
        return "google"
    return host


def device(ua: str) -> str:
    return "mobile" if re.search(r"Mobile|Android|iPhone|iPad", ua) else "desktop"


def read(since: dt.date, skip: set[str]):
    for f in sorted(CACHE.glob("*.gz")):
        try:
            text = gzip.open(f, "rt", encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        fields = None
        for line in text.splitlines():
            if line.startswith("#Fields:"):
                fields = line.split()[1:]
                continue
            if line.startswith("#") or not fields:
                continue
            row = dict(zip(fields, line.split("\t")))
            day = dt.date.fromisoformat(row.get("date", "1970-01-01"))
            if day < since:
                continue
            ua = urllib.parse.unquote(urllib.parse.unquote(row.get("cs(User-Agent)", "")))
            if (row.get("cs-method") != "GET" or row.get("cs-uri-stem") not in PAGES
                    or row.get("sc-status") not in ("200", "304")):
                continue
            if NOT_PEOPLE.search(ua) or row.get("c-ip") in skip:
                continue
            yield {"day": day, "who": (row.get("c-ip"), ua), "where": where(row.get("x-edge-location", "")),
                   "from": came_from(row.get("cs(Referer)", "-")), "device": device(ua)}


def report(views: list[dict], days: int) -> dict:
    by_day = collections.OrderedDict()
    for v in sorted(views, key=lambda v: v["day"]):
        d = by_day.setdefault(v["day"].isoformat(), {"views": 0, "who": set()})
        d["views"] += 1
        d["who"].add(v["who"])
    first = {}
    for v in sorted(views, key=lambda v: v["day"]):
        first.setdefault(v["who"], v)
    count = lambda key: collections.Counter(v[key] for v in first.values()).most_common()
    return {
        "days": days, "page_views": len(views), "visitors": len(first),
        "by_day": [{"day": k, "visitors": len(d["who"]), "views": d["views"]} for k, d in by_day.items()],
        "where": count("where"), "device": count("device"),
        # every source a visitor came through, once each: a visitor who came
        # back from a LinkedIn post counts there even if their first visit was
        # typed in
        "from": collections.Counter(src for _, src in {(v["who"], v["from"]) for v in views
                                                        if v["from"] != "this site"}).most_common(),
    }


def text(r: dict) -> str:
    out = [f"last {r['days']} days: {r['visitors']} visitors, {r['page_views']} page views",
           "(a visitor is one address with one browser; where is the CloudFront edge that answered)", ""]
    out.append("day         visitors  views")
    out += [f"{d['day']}  {d['visitors']:>8}  {d['views']:>5}" for d in r["by_day"]] or ["(no visits)"]
    for title, key in (("where", "where"), ("from", "from"), ("device", "device")):
        out += ["", title] + [f"  {n:>4}  {k}" for k, n in r[key]]
    return "\n".join(out)


def page(r: dict) -> str:
    rows = "".join(f"<tr><td>{d['day']}</td><td>{d['visitors']}</td><td>{d['views']}</td></tr>" for d in r["by_day"])
    lists = "".join(f"<h2>{t}</h2><table>" + "".join(f"<tr><td>{html.escape(str(k))}</td><td>{n}</td></tr>"
                                                    for k, n in r[key]) + "</table>"
                    for t, key in (("Where", "where"), ("From", "from"), ("Device", "device")))
    return ("<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width'>"
            "<title>Visitors</title><style>body{font:15px system-ui;margin:1.2rem;color:#16181d}"
            "table{border-collapse:collapse;margin:.4rem 0 1rem}td,th{padding:.25rem .8rem;border-bottom:1px solid #d8dbe2;"
            "text-align:left}h1{font-size:1.2rem}h2{font-size:1rem;margin-top:1.2rem}p{color:#5c6370}</style>"
            f"<h1>{r['visitors']} visitors, {r['page_views']} page views - last {r['days']} days</h1>"
            "<p>A visitor is one address with one browser. Where is the CloudFront edge that answered, near the "
            "visitor and not the visitor. Crawlers and this repository's own headless checks are not counted.</p>"
            f"<table><tr><th>day</th><th>visitors</th><th>views</th></tr>{rows}</table>{lists}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--html", help="also write the report as one HTML page")
    ap.add_argument("--json", action="store_true", help="print the report as JSON")
    a = ap.parse_args()
    sync(bucket())
    since = dt.date.today() - dt.timedelta(days=a.days - 1)
    r = report(list(read(since, excluded())), a.days)
    print(json.dumps(r, indent=1, default=str) if a.json else text(r))
    if a.html:
        pathlib.Path(a.html).write_text(page(r))
        print(f"\nwritten {a.html}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
