# 2026-07-26 — Phase 11.1c: dashboard content, written before it has ever seen a run

Chat session. Nothing was applied to AWS. The whole content of this patch is
code and documents; the cycle that exercises them is the next step, and until it
has run, every claim below is about what was written, not about what worked.

## What this step is for

11.1b built the hosting and proved it end to end against an empty bucket: a 403
with a valid certificate, which is the correct answer when there is nothing to
serve. It also wrote the status plumbing into the three lifecycle workflows and
said out loud that none of it had executed. 11.1c is the other half — the page
itself — and the first cycle in which any of that plumbing runs.

## What was written

`site/index.html`, replacing the placeholder. One file, no build step, no
dependencies, no credential of any kind:

```text
environments   status/<env>.json from this bucket: ALB, ECS service, RDS,
               the image digest prod is running, the app URL, the report URL,
               and which run wrote the file
current cycle  the public Actions API: the newest lifecycle run, its jobs, and
               EVERY STEP with state and duration — what is done, what is
               running, what has not started
history        the last twelve lifecycle runs, each labelled with the
               environment it touched
architecture   permanent levels against per-cycle levels, in the order things
               actually happen, because that split is the design
```

The per-step view is there because it was asked for explicitly while watching
`gh run watch` print exactly that: a viewer has to be able to see WHERE a cycle
is, not only whether it ended well.

## The actual design work: what the page is allowed to say

ADR-0026 says a source may only assert what it observes, and that each source is
the other's staleness detector. Turning that into a rendered panel exposed that
"the newest run" is wrong in both directions.

**Too wide.** `ci` and `publish-site` write no status file. If any newest run
made an environment stale, a documentation commit would turn both panels amber
while nothing in AWS had moved. A page that cries wolf is a page nobody reads,
and this project's whole thesis is that a signal should mean something. Fixed by
comparing each environment against the newest run that WRITES ITS FILE.

**Too narrow.** That fix depends on being able to attribute a `destroy` run to an
environment, and the anonymous Actions API does not expose `workflow_dispatch`
inputs. The page's only honest fallback is to treat such a run as possibly
affecting both and mark both unknown — correct, and useless often enough to
matter, since a destroy is half of every cycle.

One line of YAML closes it:

```yaml
run-name: destroy ${{ inputs.environment }}
```

Not cosmetic. It is what makes the run observable to the only source entitled to
describe runs. Runs from before this change still degrade to "unknown" rather
than being quietly misread, which is the same choice the page makes everywhere
else.

## Degradation, since an empty result is not a clean result

```text
GitHub API 403      a named banner with the time of the last successful read in
                    this browser session, plus "none yet" if there has not been
                    one. Never an empty history table.
no status file      "no observation" — which is not the same as "destroyed" and
                    is not rendered as though it were.
API unreadable      a panel shows its last observation labelled UNVERIFIED. The
                    bucket is still a real observation; what is missing is the
                    second source that would say whether it is the current one.
                    Half a source is not the same as a source.
stale file          "unknown", naming the run that has not reported, with the
                    last values dimmed under an explicit "for reference only".
```

Rate limit budget: 60 anonymous requests per hour per IP. A page load costs two.
The page polls only while a run is in flight, every three minutes — 40 an hour at
worst. A dashboard that exhausts its own budget while nobody is watching would be
reporting on nothing.

## Verification before anything ran

The states worth seeing are the ones a healthy cycle will not produce on demand,
so the render logic was driven through a stub DOM in the chat sandbox with six
fixtures. Each produced the intended badge and wording:

```text
ci after a destroy                  both panels destroyed — the "too wide" bug,
                                    absent
deploy-stage in flight              stage unknown, naming run #20 as in progress
status file written by that run     stage up, with the digest and the app link
no status files at all              both "no observation"
GitHub 403                          banner, history unavailable, cycle panel not
                                    filled in, two badges marked unverified
destroy with no run-name            both environments unknown, naming the run
```

This is a proxy, not a substitute — the same category as the `fmt` stand-in in
11.1a, and it should be treated with the same suspicion. What it buys is that the
failure paths were looked at at all, which a green cycle would never have done.

## What is NOT proven

- No status file has ever been written. `observe-environment.sh` and
  `publish-status.sh` have never run in a workflow.
- The `partial` state — a half-torn-down environment — has been produced by
  nothing, ever, in any environment.
- The page has never fetched a real `status/*.json` or a real run.

## Criteria to close, and the prediction

```text
1. publish-site green, https://demo.uveapp.net/ still 200
2. a full cycle with no manual AWS operation: deploy-stage -> promote-prod
   (pausing for review) -> destroy prod -> destroy stage
3. both status files exist, each written by the run that observed it, and the
   dashboard renders stage `up` during the cycle and `destroyed` after it
4. the per-stage panel is watched with a run in flight, not reconstructed
   afterwards from a finished one
5. the published Playwright report opens from the dashboard with no GitHub
   account
```

Prediction, written down so it can be wrong on the record like the last three
were: the status steps run under `if: always()` and have never executed, so the
likeliest failure is a missing IAM read or a shell assumption in
`observe-environment.sh`. Its `partial` branch is the one no environment has ever
produced.

---

# What the cycle showed (same session, after the patch landed)

One cycle, no manual AWS operation in it:

```text
publish-site  30229498666   8s     apex 200, asserted by the workflow
deploy-stage  #21          16m05s  first attempt
promote-prod  #4           14m17s  paused for a required reviewer; promoted the
                                   digest stage tested, no rebuild
destroy prod  #12           8m39s  paused for a reviewer, then green
destroy stage #13           8m31s  green
```

All five closing criteria met. The plumbing written in 11.1b executed for the
first time and was green in all four runs.

## What was watched rather than reconstructed

```text
stage   no observation -> up
prod    no observation -> up -> unknown -> destroyed
```

Each state named the run responsible. The `unknown` in the middle is the whole
design in one panel: `promote-prod` had reported `up`, a destroy was in flight,
and nothing had observed AWS since — so the page rendered neither value and said
which run it was waiting for.

Promotion by digest stopped being a sentence: stage showed `...app:70bb5d5...`
and prod `...app@sha256:094e7838...` on the same screen. `run-name` proved itself
the same way — #12 and #13 read `prod` and `stage`, while every earlier destroy
still reads `stage, prod`, the honest fallback for runs that predate it.

## Three defects, all found by running it

None would have been found by review, and all three are the same shape: the page
saying something it was not in a position to say.

```text
1  a panel with no status file said "nothing has reported" and stopped, while a
   deploy was sixteen minutes into reporting. It now names the in-flight run.
2  the step list said "step detail could not be read" while the promotion waited
   for its reviewer. GitHub returns a job with an EMPTY step list until the job
   starts; an absence had been turned into a failed read. Read-failed, queued and
   held-at-the-gate are now three different sentences, and `waiting` is named
   instead of being flattened into "running".
3  refresh was GitHub-only, every three minutes - from outside, indistinguishable
   from a dead page. The bucket is free, so it is read every 30 s; GitHub is 60
   requests an hour, so the interval is derived from the rate-limit headers it
   returns.
```

## The prediction was wrong, for the fourth time in a row

This file predicted a missing IAM read or the untested `partial` branch of
`observe-environment.sh`. Nothing on the AWS side failed at all. Every defect was
in the browser, in the half no fixture could cover because it needs a real run to
exist. `partial` is still produced by nothing: prod WAS partial mid-teardown and
the page could not show it, because only the workflow observes, and it observes
at the start and at the end.

The reasoning behind the prediction is kept rather than deleted, as the three
before it were. But four consecutive misses in the same direction is itself a
finding: this project has got good at the AWS half and keeps being surprised by
whatever it built most recently.

## A trap caught in the act

A command written IN THIS SESSION, to check the security posture:

```bash
grep -rn 'pull_request_target' .github/ || echo none
```

Run from the wrong directory, it printed `none`. `grep` exits 1 for "no matches"
and 2 for "could not look", and `||` cannot tell them apart — so a failed check
rendered exactly like a clean one, in the same session whose documents describe
that failure mode twice. The corrected form prints the exit code, so an absence
and a failure are different things on screen. Documenting a trap does not remove
it; that is now demonstrated rather than asserted.

## What this leaves for later

- `partial` has never been observed by anything.
- The UI write path against prod is still covered by nothing automated, by
  design.
- Actions logs are world-readable on a public repository, so anything a step
  prints is public. `TF_VAR_budget_email` remains the known item, named in
  `docs/security-posture.md`.
