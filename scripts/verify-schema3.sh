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
#     scripts/verify-schema3.sh
#
# Exit status: 0 only if the migration is in place, every gate passed, and the
# probe returned a non-zero count.

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
printf '%-18s %-6s %s\n' "step" "status" "note"
printf '%-18s %-6s %s\n' "------------------" "------" "----"
failed=0
for i in "${!names[@]}"; do
  if [ "${statuses[$i]}" -eq 0 ]; then
    word="ok"
  else
    word="FAIL"
    failed=$((failed + 1))
  fi
  printf '%-18s %-6s %s\n' "${names[$i]}" "$word" "${notes[$i]}"
done

if [ "$failed" -ne 0 ]; then
  echo
  echo "verify-schema3: ${failed} of ${#names[@]} steps failed"
  exit 1
fi
echo
echo "verify-schema3: ${#names[@]}/${#names[@]} green, including the real file"
