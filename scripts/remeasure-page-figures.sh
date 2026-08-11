#!/usr/bin/env bash
# THE FIGURES THIS PROJECT ARGUES FROM, REMEASURED - each on the commit it was
# recorded on, twice: once with the instrument that produced it, and once with
# the Phase 26 instrument, which serves the run layer (ADR-0060 D4/D5).
#
# It exists because a remeasurement delivered as a paragraph is the same mistake
# that made measure-page.mjs necessary: 20e's figures outlived the harness that
# produced them, which is how a number becomes folklore. This one can be run
# again, and it will disagree with the committed log if anything moves.
#
# It ran from /tmp before it was committed, and its output is
# docs/sessions/2026-08-11-phase-26-remeasurement.log. This copy differs from
# what produced that log in exactly two ways, both stated so the log's
# provenance is checkable: these comments, and `cd` resolving relative to the
# script instead of a hardcoded home directory. Every measuring line is
# unchanged. It adds detached worktrees under /tmp and removes them again.
#
#     bash scripts/remeasure-page-figures.sh 2>&1 | tee /tmp/remeasure.log
#
# Each spec is  <commit>:<fixture>:<baseline instrument>, where `own` means the
# instrument that commit carries. 21062cc names fd76351 instead, because
# ADR-0052's 1432.28px was produced by 20j's instrument - which had just gained
# `filled` - running on the page as it stood BEFORE 20j. A baseline taken with
# that commit's own script would measure air by a different definition and the
# comparison would be of two instruments, not of two pages.
set -u
cd "$(dirname "$0")/.."
export PLAYWRIGHT_MODULE=$PWD/tests/playwright/node_modules/@playwright/test/index.js
NEW=$PWD/scripts/measure-page.mjs
LAYER=$PWD/tests/fixtures/page-measure/layer

echo "=== phase 26 - the same instrument on the same commits"
echo "host: $(uname -n)   chromium: $(ls ~/.cache/ms-playwright | tr '\n' ' ')"
echo "each commit is measured twice: with the instrument it was measured by THEN,"
echo "and with the Phase 26 instrument, which serves the run layer."
echo

for spec in d5dbbaf:in-flight:own c845476:in-flight:own 21062cc:at-rest:fd76351 fd76351:at-rest:own 6d0ee53:at-rest:own; do
  c=${spec%%:*}; rest=${spec#*:}; fx=${rest%%:*}; base=${rest##*:}
  rm -rf /tmp/wt26-$c; git worktree add -q --detach /tmp/wt26-$c $c || { echo "WORKTREE FAILED $c"; continue; }
  echo "----- $c   fixture $fx   baseline instrument: $base"
  if [ "$base" != own ]; then git show $base:scripts/measure-page.mjs > /tmp/wt26-$c/scripts/measure-page.mjs; fi
  ( cd /tmp/wt26-$c && node scripts/measure-page.mjs --fixture $fx > /tmp/o-$c.out 2>&1; echo "  baseline exit=$?" )
  sed -n '3,12p' /tmp/o-$c.out; grep "columns" /tmp/o-$c.out; grep -A3 "^the floor" /tmp/o-$c.out | tail -2
  cp $NEW /tmp/wt26-$c/scripts/measure-page.mjs; cp -r $LAYER /tmp/wt26-$c/tests/fixtures/page-measure/
  ( cd /tmp/wt26-$c && node scripts/measure-page.mjs --fixture $fx > /tmp/n-$c.out 2>&1; echo "  WITH THE LAYER exit=$?" )
  sed -n '3,12p' /tmp/n-$c.out; grep "columns" /tmp/n-$c.out; grep -A3 "^the floor" /tmp/n-$c.out | tail -2
  echo
  git worktree remove --force /tmp/wt26-$c
done

# The pair ADR-0058 D6 records needs its `after` half measured by the baseline
# instrument too, and that half is the current page.
echo "----- HEAD, the baseline instrument (no layer), for the pair ADR-0058 D6 records"
rm -rf /tmp/wt26-head; git worktree add -q --detach /tmp/wt26-head HEAD
git show 440f988:scripts/measure-page.mjs > /tmp/wt26-head/scripts/measure-page.mjs
( cd /tmp/wt26-head && node scripts/measure-page.mjs --fixture at-rest > /tmp/o-head.out 2>&1; echo "  baseline exit=$?" )
sed -n '3,12p' /tmp/o-head.out; grep "columns" /tmp/o-head.out; grep -A3 "^the floor" /tmp/o-head.out | tail -2
git worktree remove --force /tmp/wt26-head

echo; echo "tree after:"; git status --short; echo "(empty = nothing was left behind)"
