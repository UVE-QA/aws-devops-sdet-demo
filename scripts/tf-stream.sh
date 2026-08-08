#!/usr/bin/env bash
# Run one terraform invocation with its `-json` event stream captured, and
# return terraform's own exit status.
#
# ADR-0039 D2. The stream is the raw material for scripts/fold-timeline.py; this
# script's whole job is to make sure it EXISTS, is attributable to one labelled
# operation, and carries an honest record of whether terraform returned at all.
#
#   TF_STREAM_DIR/<NN>-<label>.jsonl   created BEFORE terraform starts
#   TF_STREAM_DIR/<NN>-<label>.cmd     written BEFORE terraform starts
#   TF_STREAM_DIR/<NN>-<label>.rc      written AFTER terraform returns
#
# The .jsonl/.rc pair is the point. A cancelled or killed step leaves the .jsonl
# with no .rc beside it, and the fold reads that as "terraform never returned" no
# matter how complete the events look. A .rc that is present but non-zero is a
# terraform failure. Nothing else can tell those two apart after the fact.
#
# The .cmd holds the arguments, because the stream cannot say what invocation it
# came from: an apply that dies before finishing emits a change_summary whose
# operation is "plan", and a timeline reading only the stream would label a
# half-finished apply a plan. What was RUN is a fact the runner has and the
# stream does not.
#
# Usage:
#   TF_STREAM_DIR=/tmp/tf-streams scripts/tf-stream.sh <label> <terraform args...>
#
# Example:
#   scripts/tf-stream.sh apply apply -input=false -auto-approve -json tfplan
#   scripts/tf-stream.sh destroy-alb destroy -input=false -auto-approve -json \
#       -target=module.alb.aws_lb.this
#
# `-json` is the caller's to pass, and this script REFUSES without it. Appending
# it here would be wrong: `terraform apply <flags> tfplan` takes the plan file
# last, so a flag appended after the arguments lands in the wrong place. A
# refusal is checkable; a silent reordering is not.
set -uo pipefail

label="${1:?usage: tf-stream.sh <label> <terraform args...>}"
shift
[ "$#" -gt 0 ] || { echo "tf-stream.sh: no terraform arguments given" >&2; exit 2; }

: "${TF_STREAM_DIR:?TF_STREAM_DIR is not set}"

case " $* " in
  *" -json "*|*" -json") ;;
  *)
    echo "tf-stream.sh: refusing to run without -json in the terraform arguments" >&2
    echo "  given: terraform $*" >&2
    exit 2
    ;;
esac

case "$label" in
  *[!a-zA-Z0-9._-]*)
    echo "tf-stream.sh: label '$label' must be [a-zA-Z0-9._-] only" >&2
    exit 2
    ;;
esac

mkdir -p "$TF_STREAM_DIR"

# Filename order IS operation order, and it has to survive a two-digit count:
# a plain `ls` sort puts 10 before 2.
next="$(printf '%02d' "$(( $(find "$TF_STREAM_DIR" -maxdepth 1 -name '*.jsonl' | wc -l) + 1 ))")"
stream="${TF_STREAM_DIR}/${next}-${label}.jsonl"
rc_file="${TF_STREAM_DIR}/${next}-${label}.rc"
cmd_file="${TF_STREAM_DIR}/${next}-${label}.cmd"

: > "$stream"
printf '%s\n' "$*" > "$cmd_file"

echo "tf-stream: terraform $* → ${stream}"

# Only STDOUT is captured. `-json` puts the event stream on stdout; stderr
# carries whatever terraform says outside it, and merging the two would put
# non-JSON lines into the stream for the fold to trip over. stderr is left
# alone, so it still reaches the job log.
#
# tee keeps something visible in the Actions UI while the apply runs - the raw
# JSON is ugly, but a step that prints nothing for eleven minutes is worse. The
# readable rendering comes later, from the fold.
#
# The exit status is taken from PIPESTATUS, NOT from the pipeline. `set -o
# pipefail` would also work here, and a previous session in this repository lost
# an hour to a status read after a pipe that turned out to be grep's; reading
# terraform's own slot is the version of this that cannot be misread later.
terraform "$@" | tee "$stream"
status="${PIPESTATUS[0]}"

printf '%s\n' "$status" > "$rc_file"
echo "tf-stream: terraform exited ${status} (recorded in ${rc_file##*/})"

exit "$status"
