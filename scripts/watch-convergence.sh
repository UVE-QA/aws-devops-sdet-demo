#!/usr/bin/env bash
# WHEN A FIGURE WRITTEN INTO THE BUCKET REACHES A READER, measured rather than
# bounded. An INSTRUMENT, not a gate: it prints a measurement and has no verdict,
# so it is not in assets/gates.json and no break test is owed for it. What is
# owed is trust, and that is what the self-test below is for.
#
# 20m left this open and said why. Run #32 finished about 15:12:30; the next
# observation was 15:14:48 with the figures already drawn, so `max-age=60` was
# bounded above by about two minutes and never measured. The question the cursor
# actually asked - does a minute of CloudFront TTL read to a visitor as
# converging or as broken - cannot be answered by an upper bound taken from two
# glances.
#
# THE DELAY IS TWO DELAYS, AND THEY ARE FIXED IN DIFFERENT PLACES.
#
#   write -> edge   the object is PUT into S3, and the edge goes on serving its
#                   cached copy until max-age=60 expires. Bounded by the
#                   cache-control in scripts/publish-status.sh, and changed only
#                   by changing that or by invalidating.
#   edge -> reader  the page re-reads the run layer on its own 30 s tick
#                   (ADR-0053). Changed only in the page.
#
# One number covering both answers neither. So this samples the first half, and
# the second half is read off the page beside it.
#
# NO AWS CREDENTIAL IS NEEDED, and that is not a convenience - it is what lets
# this run from anywhere, against the same URL a visitor uses. Every timestamp
# it needs is in the response:
#
#   Last-Modified   when S3 took the write. The origin's own clock.
#   Date, Age       this response left the edge at Date, and the edge has held
#                   this copy for Age seconds - so the edge fetched it at
#                   (Date - Age). That is the instant the CDN converged.
#
# Therefore, for the response that first carries a new object:
#   write -> edge = (Date - Age) - Last-Modified
#   edge -> here  = <local sighting> - (Date - Age)
# and the second is bounded below by the sampling interval, which is why the
# interval is printed in the header rather than left to be remembered.
#
# A 404 IS A STATE, NOT AN ERROR. The object being deliberately absent is how
# Phase 28 exercises `not reached yet`, so its disappearance and its return are
# both transitions this must report rather than skip.
#
# Usage:
#   scripts/watch-convergence.sh <url> [seconds] [interval]
#     seconds   how long to sample for. Default 900.
#     interval  seconds between samples. Default 2.
#
#   scripts/watch-convergence.sh --self-test
#     Serves a file this script changes at an instant it knows, samples it, and
#     checks the reported transition against that known instant. An instrument
#     has to be trusted before its verdict means anything, and this project has
#     already measured a pipe, a bytecode cache and a control that reproduced
#     the defect it was controlling for.
#
# WHAT THE SAMPLER DOES TO WHAT IT MEASURES, measured in Phase 28. Polling every
# two seconds keeps a copy at the edge with a full TTL ahead of it at all times,
# so a write always lands INSIDE a sixty-second window and the delay is uniform
# in [0, 60]. A visitor who does not poll often finds no copy at the edge and
# gets the object at once. Both were seen in one cycle: two draws at 57.6s and
# 61.1s against three at 1.1s, 1.6s and 8.6s. The high numbers are the price of
# watching, not a property of the system, and a log of them without this
# paragraph would say the opposite.
#
# Output: one line per sample to stdout, and the same lines to
# $WATCH_LOG if set. `::` is the baseline, `**` a transition.
set -uo pipefail

interval_default=2
duration_default=900

now_ms() { date -u +%s%3N; }
iso_ms()  { date -u -d "@$(echo "scale=3; $1/1000" | bc)" +"%Y-%m-%dT%H:%M:%S.%3NZ" 2>/dev/null \
            || python3 -c "import sys,datetime;print(datetime.datetime.fromtimestamp(int(sys.argv[1])/1000,datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.')+f'{int(sys.argv[1])%1000:03d}Z')" "$1"; }
http_date_ms() { python3 -c "
import sys,email.utils,datetime
v=sys.argv[1].strip()
if not v: print(''); sys.exit()
t=email.utils.parsedate_to_datetime(v)
if t.tzinfo is None: t=t.replace(tzinfo=datetime.timezone.utc)
print(int(t.timestamp()*1000))
" "$1" 2>/dev/null || echo ""; }

sample() {
  # One request. Prints: <status> <age> <x-cache> <etag> <last-modified-ms> <date-ms> <body-sha>
  local url="$1" tmp hdr status age xcache etag lm dt sha
  tmp=$(mktemp); hdr=$(mktemp)
  status=$(curl -sS -o "$tmp" -D "$hdr" -w '%{http_code}' --max-time 10 "$url" 2>/dev/null || echo "000")
  age=$(grep -i '^age:' "$hdr" | tail -1 | cut -d: -f2- | tr -d ' \r')
  xcache=$(grep -i '^x-cache:' "$hdr" | tail -1 | cut -d: -f2- | tr -d '\r' | sed 's/^ *//;s/ /_/g')
  etag=$(grep -i '^etag:' "$hdr" | tail -1 | cut -d: -f2- | tr -d ' \r"')
  lm=$(http_date_ms "$(grep -i '^last-modified:' "$hdr" | tail -1 | cut -d: -f2- | sed 's/^ *//' | tr -d '\r')")
  dt=$(http_date_ms "$(grep -i '^date:' "$hdr" | tail -1 | cut -d: -f2- | sed 's/^ *//' | tr -d '\r')")
  sha=$(sha256sum "$tmp" | cut -c1-12)
  [ "$status" = "200" ] || sha="-"
  rm -f "$tmp" "$hdr"
  echo "${status} ${age:--} ${xcache:--} ${etag:--} ${lm:--} ${dt:--} ${sha}"
}

watch() {
  local url="$1" duration="${2:-$duration_default}" interval="${3:-$interval_default}"
  local started prev_key prev_change_ms line status age xcache etag lm dt sha
  started=$(now_ms)
  prev_key=""
  prev_change_ms=""
  {
    echo "# watch-convergence  url=${url}"
    echo "# interval=${interval}s duration=${duration}s  started=$(iso_ms "$started")"
    echo "# :: baseline (first sample, nothing observed to change) ; ** a transition"
    echo "# sighting is when the RESPONSE arrived; window is how long that request took, so the"
    echo "# change happened somewhere inside [sighting - window, sighting]. Late, never early."
    echo "# edge_fetch = Date - Age ; write->edge = edge_fetch - Last-Modified"
    echo "# sighting_local                status age x-cache        etag         write->edge  edge->here   window sha"
  } | tee -a "${WATCH_LOG:-/dev/null}"

  while [ $(( ($(now_ms) - started) / 1000 )) -lt "$duration" ]; do
    # THE SIGHTING IS WHEN THE ANSWER ARRIVED, NOT WHEN THE QUESTION WAS ASKED.
    # It was t0 for one version of this file, which is a timestamp that can
    # PRECEDE the event it reports: the object may change at any point between
    # the request leaving and the response landing. The devbox printed
    # `lag -0.00s` on the first real run - two milliseconds of negative, which
    # the self-test's `0 <= d` waved through only because printf had rounded
    # -0.002 to -0.00. So t1 is the sighting, t0 survives as the width of the
    # window the change could have happened in, and the reported instant is now
    # never earlier than the truth. It is LATE by at most that width, which is
    # printed rather than left to be assumed.
    local t0 t1 out
    t0=$(now_ms)
    out=$(sample "$url")
    t1=$(now_ms)
    read -r status age xcache etag lm dt sha <<<"$out"
    local key="${status}:${etag}:${sha}"
    local mark="  " w2e="-" e2h="-" win="-"
    if [ -z "$prev_key" ]; then
      # NOT A TRANSITION. The first sample is the baseline: nothing has been
      # seen to change yet, and marking it `**` puts a change in the log that
      # nobody observed.
      mark="::"
      prev_key="$key"
    elif [ "$key" != "$prev_key" ]; then
      mark="**"
      prev_key="$key"
      prev_change_ms="$t1"
    fi
    if [ "$mark" != "  " ]; then
      win=$(python3 -c "print(f'{($t1-$t0)/1000:.3f}s')")
      # AGE IS ABSENT ON EXACTLY THE INTERESTING RESPONSE. This condition used
      # to require it, and CloudFront omits `Age` on a MISS - which is the
      # response that FIRST carries a new object, the one measurement this
      # instrument exists to take. Three of the five transitions in Phase 28's
      # cycle printed `-` here and had to be reconstructed by hand from
      # head-object afterwards.
      #
      # With `Age`      the edge fetched at (Date - Age): a hit on a copy it has
      #                 been holding, and `edge->here` is the part after that.
      # Without `Age`   the edge went to the origin during THIS request, so the
      #                 fetch is inside [t0, t1] and `edge->here` is that width.
      # Either way `write->edge` needs `Last-Modified`, and that is what the
      # condition asks for now.
      if [ "$lm" != "-" ]; then
        local edge_ms
        if [ "$age" != "-" ] && [ "$dt" != "-" ]; then
          edge_ms=$(( dt - age * 1000 ))
        else
          edge_ms=$t1
        fi
        w2e=$(python3 -c "print(f'{($edge_ms-$lm)/1000:.1f}s')")
        e2h=$(python3 -c "print(f'{($t1-$edge_ms)/1000:.1f}s')")
      fi
    fi
    line=$(printf "%s %s %6s %3s %-14s %-12s %11s %11s %8s %s" \
      "$mark" "$(iso_ms "$t1")" "$status" "$age" "$xcache" "${etag:0:12}" "$w2e" "$e2h" "$win" "$sha")
    echo "$line" | tee -a "${WATCH_LOG:-/dev/null}"
    sleep "$interval"
  done
  : "${prev_change_ms:-}"
}

SELF_TEST_SERVER='
# A SERVER THAT LIES ABOUT ITS AGE, ON PURPOSE. A plain http.server sends no
# `Age`, so pointing the sampler at one exercises the transition detection and
# leaves the two computed columns empty - which is a self-test that cannot fail
# on the arithmetic it exists to check. This one emits a KNOWN `Age` and a
# `Last-Modified` a known distance behind `Date`, so `write->edge` has a right
# answer to be wrong about.
import http.server, socketserver, email.utils, datetime, pathlib, sys, threading
AGE, BEHIND = 7, 30          # seconds. write->edge must come out at BEHIND-AGE.
p = pathlib.Path(sys.argv[1])
class H(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def log_message(self, *a): pass
    def do_GET(self):
        body = p.read_bytes()
        now = datetime.datetime.now(datetime.timezone.utc)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Date", email.utils.format_datetime(now))
        self.send_header("Age", str(AGE))
        self.send_header("ETag", body.decode().strip())
        self.send_header("Last-Modified", email.utils.format_datetime(
            now - datetime.timedelta(seconds=BEHIND)))
        self.send_header("X-Cache", "Hit from cloudfront")
        self.end_headers()
        self.wfile.write(body)
srv = socketserver.TCPServer(("127.0.0.1", 0), H)
print("port", srv.server_address[1], flush=True)
srv.serve_forever()
'

self_test() {
  # A CHANGE AT AN INSTANT WE KNOW. No CDN: this checks the reporting, the
  # header parsing and the arithmetic, so that when the same code is pointed at
  # CloudFront the only new thing in the reading is the CDN.
  local dir port pid t_change first_seen rc=0
  dir=$(mktemp -d); echo "before" > "$dir/probe.json"
  printf '%s' "$SELF_TEST_SERVER" > "$dir/server.py"
  ( python3 "$dir/server.py" "$dir/probe.json" >"$dir/server.log" 2>&1 ) &
  pid=$!
  sleep 1
  port=$(grep -o 'port [0-9]*' "$dir/server.log" | head -1 | awk '{print $2}')
  if [ -z "$port" ]; then echo "self-test: could not start a server" >&2; kill $pid 2>/dev/null; return 2; fi
  ( sleep 6; date -u +%s%3N > "$dir/t_change"; echo "after" > "$dir/probe.json" ) &
  WATCH_LOG="$dir/log" watch "http://127.0.0.1:${port}/probe.json" 14 1 >/dev/null
  kill $pid 2>/dev/null; wait $pid 2>/dev/null
  t_change=$(cat "$dir/t_change" 2>/dev/null || echo "")
  first_seen=$(grep '^\*\*' "$dir/log" | tail -1 | awk '{print $2}')
  echo "--- self-test ---"
  grep -E '^(::|\*\*|  )' "$dir/log" | tail -12
  if [ -z "$t_change" ] || [ -z "$first_seen" ]; then
    echo "self-test: REFUSED - no transition was reported at all." >&2; rc=2
  else
    local seen_ms delta
    seen_ms=$(python3 -c "
import sys,datetime
print(int(datetime.datetime.strptime(sys.argv[1],'%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=datetime.timezone.utc).timestamp()*1000))" "$first_seen")
    delta=$(python3 -c "print(f'{($seen_ms-$t_change)/1000:.2f}')")
    echo "known change at   $(iso_ms "$t_change")"
    echo "reported first at $first_seen"
    echo "lag              ${delta}s   (must be > 0 and <= the 1s interval plus a request)"
    # STRICTLY POSITIVE. A sighting is the arrival of an answer, so it is always
    # LATER than the change it reports; zero or negative means the timestamp is
    # being taken on the wrong side of the request, which is what the devbox
    # printed as `-0.00s` and this check waved through on a printf rounding.
    python3 -c "
import sys
d=float('$delta')
sys.exit(0 if 0 < d <= 2.5 else 1)" || { echo "self-test: FAILED - the reported instant does not match the known one (a sighting that is not strictly later than the change is taken on the wrong side of the request)." >&2; rc=1; }
    # THE ARITHMETIC, AGAINST A SERVER WHOSE ANSWER IS KNOWN. Age 7, Last-Modified
    # 30 s behind Date, so the edge fetched it 23 s after the write, every time.
    local w2e
    # FIELD 7 BY NAME, not by counting from the end. `$(NF-2)` was right until
    # the window column was added, and then silently read `edge->here` instead -
    # the self-test failed loudly, which is the only reason this is a footnote
    # rather than a wrong number in the cycle log.
    #   1 mark  2 sighting  3 status  4 age  5 x-cache  6 etag
    #   7 write->edge  8 edge->here  9 window  10 sha
    w2e=$(grep '^\*\*' "$dir/log" | tail -1 | awk '{print $7}')
    echo "write->edge      ${w2e}   (server declares Age 7 and Last-Modified 30 s back: must be 23.0s)"
    case "$w2e" in
      2[23].[0-9]s) : ;;
      -) echo "self-test: FAILED - the arithmetic columns were never computed, so nothing checked them." >&2; rc=1 ;;
      *) echo "self-test: FAILED - write->edge came out ${w2e}, not 23.0s." >&2; rc=1 ;;
    esac
    [ $rc -eq 0 ] && echo "self-test: the instrument reports a change it did not cause, at the second it happened, and its arithmetic answers a question with a known answer."
  fi
  rm -rf "$dir"
  return $rc
}

case "${1:-}" in
  --self-test) self_test ;;
  "") echo "usage: $0 <url> [seconds] [interval]   |   $0 --self-test" >&2; exit 2 ;;
  *) watch "$@" ;;
esac
