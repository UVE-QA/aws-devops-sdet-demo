# 2026-08-02 — Phase 18: remaining documentation

Pulled forward of Phases 17 and 19, same reasoning as Phase 12 in the MVP
track: it changes no infrastructure, and the two phases still open both draw on
it — 19 in particular needs the FinOps talking points and the measured
per-cycle cost this phase writes down.

## What was built

```text
docs/cost-control.md              the permanent-vs-per-cycle split (only two
                                  of five state levels are ever destroyed),
                                  real Terraform defaults from
                                  infra/envs/stage/terraform.tfvars.example,
                                  the two cycle costs already measured
                                  closing Phase 16a ($0.09) and 16b ($0.17),
                                  cited rather than re-derived, the budget
                                  alarm's actual thresholds, and the
                                  "always destroy" rule stated as a rule
                                  rather than left implicit
docs/interview-talking-points.md  five roles - DevOps, Cloud Engineer, QA/SDET,
                                  Security, FinOps - every point traced to an
                                  ADR or a session summary. Explicitly marks
                                  Phases 17-19 as planned, not built, so the
                                  document cannot be read to claim more than
                                  the project does
docs/lightsail-devbox.md          the devbox's role versus the AWS deploy
                                  target, the SSH tunnel command, and the two
                                  non-default login flags this project has
                                  needed since Phase 1 (`--use-device-code`,
                                  `--git-protocol https --web`) with the
                                  reason for each rather than just the flag
```

No ADR. No structural decision was made — this phase reorganizes and states
what earlier phases already decided.

## What was checked, and how

None of the three joins the LIVING set `scripts/check-docs-references.py`
enforces (README.md, architecture, demo-script, phase-gates, session-primer,
transfer-buffer) — widening that list is a separate decision this phase did
not make. Every claim of the four kinds `docs-check` verifies mechanically for
the living set was instead checked by hand against this working copy before
the patch existed:

```bash
grep -ohE 'ADR-[0-9]{4}' docs/cost-control.md docs/interview-talking-points.md \
  docs/lightsail-devbox.md | sort -u
# 12 references; each resolved against docs/decisions/<n>-*.md - all present

grep -ohE 'make [a-zA-Z0-9_.-]+' <the same three files>
# 2 references (session-open, tf-validate); both real Makefile targets

# every infra/, docs/, tests/, .github/, .checkov.yaml, CLAUDE.md path cited
# in the three files, checked against `ls`/test -e individually
```

Zero findings across all three kinds. `make docs-check` was re-run unchanged
to confirm this phase did not regress the living set: 6 documents, 0 findings.

## No cycle run

Deliberate, same exception as Phase 12: no HCL, no AWS-touching workflow, and
no application code changed this session. The costs cited in
`docs/cost-control.md` are the ones already measured and recorded closing 16a
and 16b, not re-measured here.

## Documents this session edited outside the three new files

`docs/phase-gates.md` (status table row + completion-criteria section),
`docs/next-phases.md` (Phase 18 marked DONE), `docs/discussion-log.md`
(Current state block), this summary, and `docs/sessions/INDEX.md`.
`docs/session-primer.md` was NOT touched this session, so the transfer-buffer
copy does not need refreshing.

## Cost

**$0.** Nothing was applied to AWS and no environment existed at any point.
