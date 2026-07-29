#!/usr/bin/env python3
"""Summarise a Checkov JSON report, and refuse when it proves nothing.

Checkov exits 0 when it scans an empty directory: no resources, no failures,
success. That is the same shape as the gitleaks trap this repository already
carries a refusal for - an empty result is indistinguishable from a clean one.
So the gate asserts that something was actually evaluated, prints how much,
and lists what failed. It never turns a red run green: the caller keeps
Checkov's own exit status.
"""
import json
import sys


def main() -> int:
    path = sys.argv[1]
    try:
        with open(path) as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"iac-scan: cannot read {path} ({exc}). Refusing to call this a pass.")
        return 1

    blocks = data if isinstance(data, list) else [data]
    passed = failed = skipped = 0
    failures = []
    for block in blocks:
        summary = block.get("summary", {})
        passed += summary.get("passed", 0)
        failed += summary.get("failed", 0)
        skipped += summary.get("skipped", 0)
        for check in block.get("results", {}).get("failed_checks", []):
            failures.append(
                f"  {check.get('check_id')}  {check.get('file_path')}  "
                f"{check.get('resource')}\n      {check.get('check_name')}"
            )

    if passed + failed == 0:
        print(
            "iac-scan: Checkov evaluated ZERO checks. Either the directory list in "
            ".checkov.yaml no longer points at any Terraform, or the scan failed "
            "before it started. Refusing to pass without scanning anything."
        )
        return 1

    print(f"iac-scan: {passed} passed, {failed} failed, {skipped} skipped inline")
    if failures:
        print("\niac-scan: failing checks\n" + "\n".join(failures))
        print(
            "\nEach of these is a decision: fix it, or add it to skip-check in "
            ".checkov.yaml with the reason written next to it."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
