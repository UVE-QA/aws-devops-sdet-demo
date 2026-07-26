#!/usr/bin/env bash
# Every spec file on disk must belong to exactly one Playwright project.
#
# The projects in playwright.config.ts select by directory. A spec file placed
# outside tests/smoke/ and tests/regression/ matches neither, so Playwright
# runs it in no project and reports nothing about it — a test that silently
# does not exist. That is the same failure shape as a `make tf-validate` that
# discovers zero root levels and exits green, and it is caught the same way:
# by asserting on the discovery itself rather than trusting it.
#
# Parsed with node, not jq: node is already required to run Playwright at all,
# so this adds no tool the caller might not have.
set -euo pipefail

cd "$(dirname "$0")/.."

# Paths in the JSON report are relative to Playwright's rootDir, which is the
# common base of the test files and therefore NOT the same prefix `find` emits.
# Both sides are normalised to the part after tests/ so the comparison is about
# which files there are, not about how each side spells the prefix.
on_disk="$(find tests -name '*.spec.ts' | sed 's|^\./||; s|^tests/||' | sort)"
if [ -z "$on_disk" ]; then
  echo "assert-spec-coverage: no spec files found at all. Refusing to pass."
  exit 1
fi

known="$(npx playwright test --list --reporter=json \
  | node -e '
      let raw = "";
      process.stdin.on("data", (c) => (raw += c));
      process.stdin.on("end", () => {
        const files = new Set();
        const walk = (node) => {
          if (!node || typeof node !== "object") return;
          if (Array.isArray(node)) return node.forEach(walk);
          if (typeof node.file === "string") files.add(node.file);
          Object.values(node).forEach(walk);
        };
        walk(JSON.parse(raw).suites || []);
        console.log([...files].map((f) => f.replace(/^tests\//, "")).sort().join("\n"));
      });
    ')"
if [ -z "$known" ]; then
  echo "assert-spec-coverage: Playwright resolved zero spec files. Refusing to pass."
  exit 1
fi

if ! diff <(echo "$on_disk") <(echo "$known") >/dev/null; then
  echo "assert-spec-coverage: spec files on disk do not match the files Playwright will run."
  echo
  echo "  on disk:"; echo "$on_disk" | sed 's/^/    /'
  echo "  resolved by Playwright:"; echo "$known" | sed 's/^/    /'
  echo
  echo "A spec must live under tests/smoke/ (read-only, runs everywhere) or"
  echo "tests/regression/ (destructive, never prod). Anything else is invisible."
  exit 1
fi

count="$(echo "$on_disk" | wc -l | tr -d ' ')"
echo "assert-spec-coverage: OK — $count spec file(s), all resolved by a project"
