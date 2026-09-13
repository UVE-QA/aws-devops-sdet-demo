#!/usr/bin/env bash
#
# THE DEAD-LETTER PATH, EXERCISED (Phase 42, ADR-0096).
#
# The worker leaves a message it can never process, so the queue's redrive
# policy carries it to the dead-letter queue after three receipts, where the
# alarm is. Every part of that sentence is a thing that can silently not
# happen: a worker that deletes what it cannot parse empties the dead-letter
# queue for ever; a redrive policy nobody attached leaves poison cycling in the
# main queue; a visibility timeout of thirty seconds makes three receipts a
# minute and a half nobody waits for. So this sends one body that is not an
# event into the LOCAL queue and waits for it to arrive in the dead-letter
# queue - and refuses if it takes longer than the local redrive should, or if
# the main queue still holds it.
#
# Needs the local stack up (make local-up). The alarm itself is AWS's and is
# checked by a cycle, not here; what this holds still is the worker's half.
#
# Usage: scripts/break-poison-message.sh

set -euo pipefail

MAIN="http://elasticmq:9324/000000000000/items"
DLQ="http://elasticmq:9324/000000000000/items-dlq"
q() { docker compose --progress quiet run --rm --no-deps -T worker python scripts/sqs_tool.py "$@"; }

echo "=== control: the worker is up and the dead-letter queue is empty ==="
state="$(docker compose ps --format '{{.Service}} {{.Health}}' worker 2>/dev/null || true)"
case "$state" in
  *healthy*) echo "worker: $state" ;;
  *) echo "FAIL: the worker is not healthy ($state) - a poison message would just sit there"; exit 1 ;;
esac
before="$(q depth "$DLQ")"
if [ "$before" != "0" ]; then
  echo "dead-letter queue holds $before message(s) before the test; purging so the count below means something"
  q purge "$DLQ"
fi

echo "=== send one body that is not an event ==="
id="$(q poison)"
echo "sent $id"

# 3 receipts x 5 s visibility, plus the worker's long poll. 60 s is twice that.
echo "=== wait for it in the dead-letter queue ==="
deadline=$((SECONDS + 60))
depth=0
while [ "$SECONDS" -lt "$deadline" ]; do
  depth="$(q depth "$DLQ")"
  [ "$depth" != "0" ] && break
  sleep 3
done
if [ "$depth" = "0" ]; then
  echo "FAIL: nothing reached the dead-letter queue in 60 s. Either the worker deleted"
  echo "      the message, or the redrive policy is not on the queue."
  exit 1
fi
echo "dead-letter queue: $depth message(s)"

echo "=== the main queue no longer holds it ==="
main="$(q depth "$MAIN")"
if [ "$main" != "0" ]; then
  echo "FAIL: the main queue still holds $main message(s) - poison is cycling, not dead-lettered"
  exit 1
fi

echo "=== the worker said why, three times ==="
# Counted by THIS message's id, not by the phrase: the log carries every earlier
# run of this script too, and six refusals over two runs is not three over one.
said="$(docker compose logs --no-log-prefix worker 2>/dev/null | grep '"poison message left' | grep -c "\"message_id\": \"$id\"" || true)"
if [ "$said" -lt 3 ]; then
  echo "FAIL: the worker logged the poison $said time(s); three receipts should be three refusals"
  exit 1
fi
echo "refused $said time(s)"

q purge "$DLQ"
echo "OK: poison reached the dead-letter queue after three receipts and the worker kept running."
