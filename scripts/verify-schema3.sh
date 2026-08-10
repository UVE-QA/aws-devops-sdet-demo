#!/usr/bin/env bash
#
# Phase 22's runner: migrate, rebuild, and then ask every gate AND the real file.
#
# WHY THE REAL-DATA PROBE IS IN HERE WITH THE GATES
# -------------------------------------------------
# Every gate below was GREEN while all four consumers of site/data/topology.json
# were broken, because each one reads a frozen schema-2 fixture: the fixture and
# the code agreed with each other and neither had seen the file the code is
# actually handed. So a green table proves nothing on its own, and the last row
# of it is the one that would have caught 22 on the day it broke - it joins
# against site/data/topology.json itself and counts what came back.
#
# WHY EVERY STATUS IS TAKEN INTO A VARIABLE ON ITS OWN LINE
# ---------------------------------------------------------
# `$?` after a pipeline is the LAST command's status: `make gate | grep -q ok`
# reports on grep, and a gate that failed while grep matched its own error text
# reads as a pass. Nothing here is piped, tee'd or `if`-wrapped before its status
# is read.
#
# WHY THE BROWSER GATES ARE IN THE TABLE EVEN WHEN THEY CANNOT RUN
# ----------------------------------------------------------------
# The first version of this runner listed the eight gates that need no browser
# and stopped there. page-freshness-check needs chromium, was not in the list,
# and was the ONE gate that caught 22's second defect - an open tab holding the
# previous cycle's figures because a function had been written into the map's
# wrapped script and called from the dashboard's. It went to another host green
# on twelve rows.
#
# So the browser gates are rows here whatever happens. When chromium is present
# they run; when it is not they are printed as SKIP, with what is missing and
# the command that would install it. A gate that is absent from the table looks
# exactly like a gate that passed, and that is precisely how this one reached
# another machine.
#
#     scripts/verify-schema3.sh
#
# Exit status: 0 only if the migration is in place, every gate that RAN passed,
# and the probe returned a non-zero count. A SKIP does not fail the run - it is
# reported, loudly, and the summary says the verification is incomplete.

set -u

cd "$(dirname "$0")/.." || exit 1

GATES=(
  docs-check
  site-data-check
  site-page-check
  timeline-check
  node-states-check
  results-check
  live-state-check
  page-tense-check
)

# The gates that open the built page in chromium. They answer the questions no
# lifted block can: whether an open tab converges on what a reload shows, and
# whether what is drawn can be read.
BROWSER_GATES=(
  page-freshness-check
  contrast-check
)

# The same three places check-page-freshness.mjs, check-contrast.mjs and
# measure-page.mjs look, in the same order. Asked here rather than inferred from
# a gate's exit status: those scripts exit 2 both when Playwright is missing and
# when they refuse to measure something, and treating a refusal as "no browser"
# is how a red gate becomes a skipped one.
browser_ready() {
  if [ -n "${PLAYWRIGHT_MODULE:-}" ] && [ -f "${PLAYWRIGHT_MODULE}" ]; then return 0; fi
  if [ -f tests/playwright/node_modules/@playwright/test/index.js ]; then return 0; fi
  if [ -f tests/playwright/node_modules/playwright/index.js ]; then return 0; fi
  return 1
}

# A status of its own, because a skip is neither. It prints, it is counted, and
# it makes the closing line say the verification is incomplete.
SKIP=99

# The probe. Deliberately the one from the phase brief, verbatim: it loads
# node-states.py by path, hands it the REAL topology, and counts the addresses
# index_members() found for stage. Before 22 it printed 0 while every gate below
# printed ok.
PROBE=$(cat <<'PY'
import json, importlib.util as u
s = u.spec_from_file_location("ns", "scripts/node-states.py")
m = u.module_from_spec(s)
s.loader.exec_module(m)
print(len(m.index_members(json.load(open("site/data/topology.json")), "stage")))
PY
)

names=()
statuses=()
notes=()

record() {
  names+=("$1")
  statuses+=("$2")
  notes+=("$3")
}

echo "== migrate =="
python3 scripts/migrate-schema3.py
migrate_status=$?
# 3 is the patch script's "already applied" refusal, and it is the normal state
# of every run of this script after the first. Anything else non-zero is a real
# refusal and the tree has not moved.
if [ "$migrate_status" -eq 0 ]; then
  record migrate 0 "applied"
elif [ "$migrate_status" -eq 3 ]; then
  record migrate 0 "already applied"
else
  record migrate "$migrate_status" "REFUSED — nothing was written"
fi

if [ "$migrate_status" -eq 0 ] || [ "$migrate_status" -eq 3 ]; then
  echo
  echo "== rebuild =="
  make site-page
  page_status=$?
  record site-page "$page_status" "site/index.html"

  make site-data
  data_status=$?
  record site-data "$data_status" "site/data/topology.json"
fi

echo
echo "== gates =="
for gate in "${GATES[@]}"; do
  echo "-- $gate"
  make "$gate"
  gate_status=$?
  record "$gate" "$gate_status" ""
done

echo
echo "== browser gates =="
if browser_ready; then
  for gate in "${BROWSER_GATES[@]}"; do
    echo "-- $gate"
    make "$gate"
    gate_status=$?
    record "$gate" "$gate_status" ""
  done
else
  echo "no Playwright at tests/playwright/node_modules — these are NOT being run:"
  for gate in "${BROWSER_GATES[@]}"; do
    echo "   $gate"
    record "$gate" "$SKIP" "no Playwright here — run: (cd tests/playwright && npm ci)"
  done
  # Named on its own line as well as in the table, because 22's second defect
  # left this host on twelve green rows and the other host on three red cases.
  echo "page-freshness-check is the gate that caught 22's stale-figures defect."
  echo "A run of this script without it has NOT verified that an open tab converges."
fi

echo
echo "== the real file =="
# Captured, not piped: the status below is python's. An empty answer and a
# crashed interpreter are different failures and both are non-zero here.
probe_out=$(python3 -c "$PROBE" 2>&1)
probe_status=$?
if [ "$probe_status" -ne 0 ]; then
  record probe 1 "the join threw: ${probe_out}"
elif [ "$probe_out" = "0" ]; then
  # THE ROW THAT MATTERS. Zero addresses means node-states.py is reading a
  # shape site/data/topology.json no longer has, and every gate above can be
  # green while it is true.
  record probe 1 "index_members(stage) = 0 — the join found nothing in the real file"
else
  record probe 0 "index_members(stage) = ${probe_out} addresses"
fi
echo "index_members(topology, \"stage\") -> ${probe_out}"

echo
echo "== verify-schema3 =="
printf '%-20s %-6s %s\n' "step" "status" "note"
printf '%-20s %-6s %s\n' "--------------------" "------" "----"
failed=0
skipped=0
for i in "${!names[@]}"; do
  if [ "${statuses[$i]}" -eq "$SKIP" ]; then
    word="SKIP"
    skipped=$((skipped + 1))
  elif [ "${statuses[$i]}" -eq 0 ]; then
    word="ok"
  else
    word="FAIL"
    failed=$((failed + 1))
  fi
  printf '%-20s %-6s %s\n' "${names[$i]}" "$word" "${notes[$i]}"
done

ran=$(( ${#names[@]} - skipped ))
if [ "$failed" -ne 0 ]; then
  echo
  echo "verify-schema3: ${failed} of ${ran} steps that ran failed"
  exit 1
fi
echo
if [ "$skipped" -ne 0 ]; then
  # Not an exit code, a sentence: the run is green as far as it went, and how
  # far it went is the part a reader has to carry to the next host.
  echo "verify-schema3: ${ran}/${ran} green — INCOMPLETE, ${skipped} gate(s) skipped for want of a browser"
  echo "Run these where chromium is: make ${BROWSER_GATES[*]}"
  exit 0
fi
echo "verify-schema3: ${ran}/${ran} green, including the real file and the browser"
