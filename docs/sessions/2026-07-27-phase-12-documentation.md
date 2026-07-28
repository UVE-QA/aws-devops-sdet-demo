# 2026-07-27 — Phase 12: minimum viable documentation

Chat session. **Nothing was applied to AWS and nothing was destroyed.** Cost
$0. Everything below is documents, one script, and one new gate.

## What the phase owed

`docs/next-phases.md` Phase 12: a README, an architecture document, a demo
script, and the two places already known to be stale — `project-prompt.md` §7
and §10, and the `tf-workflow` and `teardown` skills.

The state was loaded from a fresh clone of `origin/main` rather than from any
copy, per ADR-0019. `HEAD` was `0c6c93e` and matched `origin/main`; `outbox/`
was empty; the MacBook's primer copy was byte-identical to
`docs/session-primer.md`. Four claims checked in about twenty seconds, and the
project has been burned by every one of them at least once.

Two of the owed items turned out to be already done or already false:

```text
teardown skill    already lists five permanent levels - fixed in 11.1b, exactly
                  where its closing criterion said it would be. Nothing to do.
README.md         not "stale". ABSENT, and absent from the entire history:
                  `git log --all -- README.md` returned nothing. Phase 8 chose
                  not to commit a false one, which is the right call and left
                  this phase with a blank page rather than an edit.
```

## What was written

```text
README.md                 what it is, how to run it, what it proves. Every
                          command in it exists in the Makefile or a workflow.
docs/architecture.md      the request path, the seven state levels, and the
                          trade-offs made on purpose: no NAT and what it costs
                          in teardown ordering, the ALB destroyed first, two
                          certificates in two regions for one domain.
docs/demo-script.md       ten minutes with no waiting in them.
docs/transfer-buffer.md   how a chat's work reaches git.
scripts/send.sh           the tool that does it, now in git.
scripts/check-docs-...py  `make docs-check`, wired into ci.yml.
ADR-0028                  control-layer tooling lives in the repository.
```

## Three decisions worth recording

**The diagram is drawn twice, and the file says so.** The same architecture is
already rendered in `site/index.html`. "Draw it once" was the plan's
instruction, and the honest reading is that the source of truth is neither
picture: it is the set of directories under `infra/`. `docs/architecture.md`
uses Mermaid — it renders on GitHub with no build step — and states plainly
which artifact wins when they disagree. A single shared SVG was the alternative
and was rejected as more machinery than the divergence risk warrants.

**No cycle was run, deliberately.** The standing invariant is that a destroy
passes end to end at the end of every phase. This phase changed no HCL, no
AWS-touching workflow and no application code, so a cycle would have proven only
what 2026-07-26 already proved, for about 45 minutes and one billable
deploy/destroy pair. The exception is written into `docs/phase-gates.md` rather
than left silent: an invariant skipped quietly is indistinguishable from one
forgotten. Phase 13 is a full empty-to-empty run and is next.

**ADR-0028**: `send.sh` and the buffer README moved into the repository. The
buffer's own README had left this open *for an ADR*, with a real argument
against — moving `send.sh` in recreates the two-copies problem, because it has
to exist on the MacBook to run. It lost on rate of change: the primer went stale
three times in one session, `send.sh` has changed once. Being outside git is
also what made its known bug unfixable, and the bug is fixed in the same commit.

## What running things found that reading them would not

Everything below was found by executing something, and none of it by review.

```text
1. `git log --all -- README.md` is empty. The phase was planned as "rewrite the
   stale README"; there was nothing to rewrite. One command, and the shape of
   the work changed.
2. The Mermaid blocks were PARSED with mermaid's own parser, not eyeballed.
   They were valid - but the check was then made to fail twice on purpose, on a
   malformed diagram and on a file with no diagram at all, because a checker
   that finds nothing to check is the e1e577a shape again.
3. `send.sh`'s new lookup was exercised in all three cases before shipping.
   Case three passed only because `set -e` exempts a failing test in an AND
   list; it was rewritten as an explicit `if`, since a correctness resting on
   that exemption is not one to build on.
4. `make docs-check` found a false claim in `docs/phase-gates.md` that had been
   sitting in the cursor since Phase 6 - the assert-seed script named by a path
   that exists only inside the image. It then caught the same mistake again in
   the paragraph being written to describe the catch.
5. The gate was seen red six times before it shipped, including once for its own
   living-document list going missing. It also produced two false positives on
   first run - `app/app/<task-id>` is a CloudWatch log stream, and "make that
   possible" is English - which is why the make-target rule now only applies
   inside code spans.
```

## The stale-command fix went everywhere, in one commit

The `tf-workflow` skill taught `terraform init -backend=false && terraform
validate` as the credential-free way to validate. Phase 9.0 established that the
flag does not skip a backend already initialized for real: it reuses the cached
S3 configuration and reads remote state.

Phase 10 recorded the general form of this — documenting a trap once does not
remove it while the wrong command stays copyable, and `--use-device-code` was
the example, written in one file while eight others printed the flagless form.
So this fix went to every copyable occurrence in the same commit:
`project-prompt.md` §11.1 and §14, and the Phase 4 validation block in
`phase-gates.md`, which now prints the superseded command marked `DO NOT USE`
beside the current one rather than quietly holding the old one. `ci.yml` was
checked rather than assumed: it runs `make tf-validate`.

## Prediction, recorded so it can be wrong in writing

The last four predictions in this project were all wrong, which is itself the
pattern: failure keeps arriving from the half nobody modelled. This phase's
prediction is that **the first genuinely new reader finds something in the
README that is true but unusable** — an instruction that assumes context the
writer had and the reader does not. `make docs-check` cannot see that class of
defect at all: every command in these documents exists, and existing is not the
same as being enough. Phase 13 performs the run "as if by a stranger", which is
the closest thing available to a test of it.

## State at the end

```text
AWS            untouched. Five permanent levels, both environments destroyed.
docs-check     6 documents, 0 findings
mermaid        3 blocks, 0 invalid
git            four commits on top of 0c6c93e
```

`docs/session-primer.md` WAS edited this session (the bare-name trap is now
described as fixed, and the buffer layout names each file's source). **The
MacBook copy must be refreshed**, per the rule in that file:

```text
scp devbox:aws-devops-sdet-demo/docs/session-primer.md ~/Projects/_claude-transfer/
scp devbox:aws-devops-sdet-demo/scripts/send.sh        ~/Projects/_claude-transfer/
scp devbox:aws-devops-sdet-demo/docs/transfer-buffer.md ~/Projects/_claude-transfer/README.md
```

Next: **Phase 13**, the MVP verification gate — one uninterrupted run from an
empty account state back to an empty account state, performed as if by a
stranger.
