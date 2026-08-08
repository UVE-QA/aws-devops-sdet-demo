#!/usr/bin/env bash
# Regenerate the timeline fixtures from a REAL terraform run.
#
# These fixtures are not hand-written JSON. Every stream under cases/ is the
# actual `-json` output of a terraform invocation, because the thing being
# tested is a fold of Terraform's event schema and a fixture invented from the
# documentation would only ever test what its author believed the schema was.
# This repository has a name for the alternative: a break test that fails to
# break is testing your assumption about the tool.
#
# It costs nothing and touches no cloud. Every resource here is the BUILT-IN
# `terraform_data`, which needs no provider plugin, so `terraform init` runs
# offline and no AWS credential is involved at any point.
#
# Usage:
#   tests/fixtures/timeline/generate.sh          # into the checked-in cases/
#   tests/fixtures/timeline/generate.sh /tmp/out # somewhere else, to compare
#
# The tool is whatever `terraform` resolves to on PATH; its version is recorded
# in cases/GENERATED-BY so a fixture can never quietly claim to have come from a
# version it did not.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
dest="${1:-${here}/cases}"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

tf() { terraform "$@"; }

say() { printf '\n== %s\n' "$*"; }

# Only the streams are regenerated. expected.json is the HUMAN half of a
# fixture - it says what the case is supposed to mean - and an earlier version of
# this function wiped the whole case directory, which deleted every expectation
# the moment anyone regenerated. The gate went from green to "no expected.json"
# in five cases at once, which is at least loud; a subtler version of the same
# mistake would have been silent.
new_case() {
  local name="$1"
  rm -rf "${dest:?}/${name}/streams"
  mkdir -p "${dest}/${name}/streams"
}

# Capture one invocation the same way scripts/tf-stream.sh does: arguments to
# the .cmd, stdout to the stream, exit code to the .rc beside it.
capture() {
  local case_name="$1" stream_name="$2" dir="$3"
  shift 3
  local out="${dest}/${case_name}/streams/${stream_name}.jsonl"
  local rc="${dest}/${case_name}/streams/${stream_name}.rc"
  local cmd="${dest}/${case_name}/streams/${stream_name}.cmd"
  : > "$out"
  printf '%s\n' "$*" > "$cmd"
  local status=0
  ( cd "$dir" && terraform "$@" ) > "$out" || status=$?
  printf '%s\n' "$status" > "$rc"
  echo "  ${stream_name}: exit ${status}, $(wc -l < "$out") events"
}

mkdir -p "$dest"

# ---------------------------------------------------------------------------
say "apply-complete — plan and apply in one invocation"
new_case apply-complete
mkdir -p "$work/complete"
cat > "$work/complete/main.tf" <<'EOF'
resource "terraform_data" "alpha" {
  input = "one"
}

resource "terraform_data" "beta" {
  input      = "two"
  depends_on = [terraform_data.alpha]
}

resource "terraform_data" "gamma" {
  count = 2
  input = "three-${count.index}"
}
EOF
( cd "$work/complete" && tf init -input=false -no-color > /dev/null )
capture apply-complete 01-apply "$work/complete" apply -input=false -auto-approve -json

# ---------------------------------------------------------------------------
# The shape deploy-stage and promote-prod actually use: plan to a file, then
# apply that file. It emits ONE change_summary, not two, which is exactly the
# kind of difference a hand-written fixture would have got wrong.
say "apply-from-plan — terraform apply tfplan"
new_case apply-from-plan
mkdir -p "$work/fromplan"
cp "$work/complete/main.tf" "$work/fromplan/main.tf"
( cd "$work/fromplan" && tf init -input=false -no-color > /dev/null )
( cd "$work/fromplan" && tf plan -input=false -out=tfplan > /dev/null )
capture apply-from-plan 01-apply "$work/fromplan" apply -input=false -auto-approve -json tfplan

# ---------------------------------------------------------------------------
say "apply-errored — a resource fails, later ones never start"
new_case apply-errored
mkdir -p "$work/errored"
cat > "$work/errored/main.tf" <<'EOF'
resource "terraform_data" "ok_one" {
  input = "one"
}

resource "terraform_data" "doomed" {
  input      = "boom"
  depends_on = [terraform_data.ok_one]

  provisioner "local-exec" {
    command = "echo 'the provisioner is about to fail' >&2; exit 7"
  }
}

resource "terraform_data" "never_reached" {
  input      = "three"
  depends_on = [terraform_data.doomed]
}
EOF
( cd "$work/errored" && tf init -input=false -no-color > /dev/null )
capture apply-errored 01-apply "$work/errored" apply -input=false -auto-approve -json

# ---------------------------------------------------------------------------
# The case the whole gate exists for. terraform is KILLED mid-apply, so the
# stream ends in the middle of a resource and no .rc is ever written - which is
# what a cancelled workflow step leaves behind. Nothing is truncated by hand.
say "apply-killed — terraform killed mid-apply, no exit code"
new_case apply-killed
mkdir -p "$work/killed"
cat > "$work/killed/main.tf" <<'EOF'
resource "terraform_data" "quick" {
  input = "one"
}

resource "terraform_data" "slow" {
  input      = "two"
  depends_on = [terraform_data.quick]

  provisioner "local-exec" {
    command = "sleep 60"
  }
}

resource "terraform_data" "after" {
  input      = "three"
  depends_on = [terraform_data.slow]
}
EOF
( cd "$work/killed" && tf init -input=false -no-color > /dev/null )
killed_stream="${dest}/apply-killed/streams/01-apply.jsonl"
: > "$killed_stream"
printf '%s\n' "apply -input=false -auto-approve -json" \
  > "${dest}/apply-killed/streams/01-apply.cmd"
( cd "$work/killed" && terraform apply -input=false -auto-approve -json > "$killed_stream" ) &
runner=$!
sleep 6
pkill -9 -P "$runner" 2>/dev/null || true
kill -9 "$runner" 2>/dev/null || true
wait "$runner" 2>/dev/null || true
sleep 1
echo "  01-apply: killed, no .rc written, $(wc -l < "$killed_stream") events"

# ---------------------------------------------------------------------------
# The same complete stream with its .rc removed, which is what a process killed
# in the window between finishing and recording its status leaves. Every event
# says the apply worked; the fold must still refuse to call it complete, because
# it cannot prove terraform returned. It exists as its own case because
# apply-killed is over-determined - three signals are missing there at once, so
# it cannot show which one is doing the work.
say "apply-complete-no-rc — a finished stream whose exit code was never recorded"
new_case apply-complete-no-rc
cp "${dest}/apply-complete/streams/01-apply.jsonl" "${dest}/apply-complete-no-rc/streams/"
cp "${dest}/apply-complete/streams/01-apply.cmd" "${dest}/apply-complete-no-rc/streams/"
echo "  01-apply: copied from apply-complete, .rc deliberately absent"

# ---------------------------------------------------------------------------
# destroy.yml's shape: the ALB is destroyed on its own first, then everything
# else. Two invocations, one timeline.
say "destroy-cycle — a targeted destroy followed by the full one"
new_case destroy-cycle
mkdir -p "$work/destroy"
cp "$work/complete/main.tf" "$work/destroy/main.tf"
( cd "$work/destroy" && tf init -input=false -no-color > /dev/null )
( cd "$work/destroy" && tf apply -input=false -auto-approve > /dev/null )
capture destroy-cycle 01-destroy-alpha "$work/destroy" \
  destroy -input=false -auto-approve -json -target=terraform_data.alpha
capture destroy-cycle 02-destroy "$work/destroy" destroy -input=false -auto-approve -json

# ---------------------------------------------------------------------------
# EVERY resource this project applies lives inside a module, and none of the
# cases above has one. So `hook.resource.module` and what `addr` looks like
# inside a module were the last piece of the schema still read from the
# documentation rather than observed — and scripts/node-states.py matches those
# addresses against the module addresses in site/data/topology.json, so a wrong
# guess there would light no node at all.
#
# A local module holding terraform_data is as real a terraform run as the others
# and costs the same nothing. Three shapes, because the address of each is
# different and the normalisation has to survive all three:
#
#   module.child.terraform_data.only        a plain resource inside a module
#   module.child.terraform_data.many[0]     count INSIDE a module - what
#                                           aws_subnet.public actually is
#   module.pair[0].terraform_data.only      count on the MODULE. infra/ has none
#                                           today, and a normalisation rule
#                                           written for a shape nobody exercised
#                                           is the class of thing this repository
#                                           breaks on purpose
say "apply-module — resources inside modules, the shape infra/ actually uses"
new_case apply-module
mkdir -p "$work/module/modules/child"
cat > "$work/module/modules/child/main.tf" <<'EOF'
variable "label" {
  type = string
}

resource "terraform_data" "only" {
  input = var.label
}

resource "terraform_data" "many" {
  count = 2
  input = "${var.label}-${count.index}"
}
EOF
cat > "$work/module/main.tf" <<'EOF'
resource "terraform_data" "root" {
  input = "at the root"
}

module "child" {
  source = "./modules/child"
  label  = "child"
}

module "pair" {
  count  = 2
  source = "./modules/child"
  label  = "pair"
}
EOF
( cd "$work/module" && tf init -input=false -no-color > /dev/null )
capture apply-module 01-apply "$work/module" apply -input=false -auto-approve -json

# ---------------------------------------------------------------------------
version_line="$(terraform version | head -1)"
printf '%s\ngenerated %s by tests/fixtures/timeline/generate.sh\n' \
  "$version_line" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "${dest}/GENERATED-BY"

say "done"
echo "$version_line"
echo "fixtures in ${dest}"
