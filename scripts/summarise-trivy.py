#!/usr/bin/env python3
"""Decide whether a Trivy report should stop the build, and say why.

The scan itself is run with --exit-code 0 and NO --ignore-unfixed, so the
report that gets uploaded contains every HIGH and CRITICAL finding, fixable or
not. The gate is applied here instead, over three questions the scanner's own
exit code cannot separate:

  is there a fix?    A HIGH with no upstream fix is not a decision anyone can
                     act on today. Gating on it produces a red build that
                     stays red until someone else releases something, which
                     trains people to ignore the gate. It is reported and not
                     gated - and the report is the point, because "we do not
                     gate on it" is not the same as "we do not know about it".
  is it allowlisted? .trivyignore carries the exceptions, each with a reason
                     written beside it, exactly like .checkov.yaml.
  did we scan at all? Trivy prints a report for an image it found nothing in,
                     and an image with no packages looks identical to a clean
                     one. A report with no results is a refusal, not a pass.
"""
import json
import os
import sys

IGNORE_FILE = ".trivyignore"


def load_allowlist() -> dict[str, str]:
    """CVE id -> the reason written above or beside it."""
    allowed: dict[str, str] = {}
    if not os.path.exists(IGNORE_FILE):
        return allowed
    reason = ""
    for raw in open(IGNORE_FILE):
        line = raw.strip()
        if not line:
            reason = ""
            continue
        if line.startswith("#"):
            reason = (reason + " " + line.lstrip("# ").strip()).strip()
            continue
        allowed[line.split()[0]] = reason or "(no reason recorded)"
    return allowed


def main() -> int:
    path = sys.argv[1]
    try:
        with open(path) as handle:
            report = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"image-scan: cannot read {path} ({exc}). Refusing to call this a pass.")
        return 1

    results = report.get("Results") or []
    if not results:
        print(
            "image-scan: the report contains NO results at all. Either the image has "
            "no package metadata Trivy understands, or the scan failed before it "
            "started. An empty report is not a clean report - refusing."
        )
        return 1

    allowed = load_allowlist()
    fixable: list[tuple[str, str, str, str]] = []
    unfixed: list[tuple[str, str, str]] = []
    allowlisted: list[tuple[str, str]] = []

    for result in results:
        for vuln in result.get("Vulnerabilities") or []:
            cve = vuln.get("VulnerabilityID", "?")
            pkg = vuln.get("PkgName", "?")
            sev = vuln.get("Severity", "?")
            fix = vuln.get("FixedVersion") or ""
            if cve in allowed:
                allowlisted.append((cve, pkg))
            elif fix:
                fixable.append((sev, cve, pkg, fix))
            else:
                unfixed.append((sev, cve, pkg))

    targets = ", ".join(str(r.get("Target")) for r in results)
    print(
        f"image-scan: {report.get('ArtifactName')} - "
        f"{len(fixable)} fixable, {len(unfixed)} with no fix available, "
        f"{len(allowlisted)} allowlisted (HIGH/CRITICAL only)"
    )
    print(f"image-scan: targets scanned: {targets}")

    for sev, cve, pkg in sorted(unfixed):
        print(f"  no fix yet   {sev:8} {cve:20} {pkg}")
    for cve, pkg in sorted(allowlisted):
        print(f"  allowlisted  {'':8} {cve:20} {pkg}  # {allowed[cve]}")
    for sev, cve, pkg, fix in sorted(fixable):
        print(f"  FIXABLE      {sev:8} {cve:20} {pkg} -> {fix}")

    if fixable:
        print(
            f"\nimage-scan: {len(fixable)} HIGH/CRITICAL findings have a fix available. "
            "Take the fix, or add the id to .trivyignore with the reason beside it."
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
