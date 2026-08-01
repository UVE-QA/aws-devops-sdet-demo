# CLAUDE.md — Project Operating Guide

This file is read at the start of every Claude Code session. It is the anchor
that does not depend on skill auto-triggering. Read it, then proceed.

## What this repo is

`aws-devops-sdet-demo` — a phase-gated AWS DevOps/SDET demo platform.
Work proceeds phase by phase (Phase 0 → Phase 8). Do not jump ahead.
The environment is brought up, demoed, and torn down repeatedly to avoid cost.

Key infra invariants (full detail in `docs/decisions/`):

- AWS profile: `demo-admin` (local SSO) / GitHub OIDC (CI). No static keys.
- Region: `us-west-2`. Deploy only into the dedicated demo member account.
- Terraform remote state in S3, in SEPARATE levels. `infra/bootstrap`
  (bucket) and `infra/bootstrap-oidc` (OIDC provider + deploy roles) are
  permanent and never destroyed by CI; only `infra/envs/*` are torn down.
  A fourth permanent level `infra/public-site` arrives in Phase 11.
- DB password via Secrets Manager, never in repo.
- No NAT Gateway, no EKS in v0.

## Start of every session (do this first)

**Run `make session-open`.** It refuses on a dirty tree, an unpushed previous
session or the wrong branch, pulls fast-forward only, and prints the current
phase from the cursor. The steps below are what it cannot do (ADR-0033).

0. Read `docs/session-primer.md` — reading order, working agreements and
   the traps that are currently live. It is a pointer, not a summary.
1. `git pull` to get the current source of truth.
2. Read `docs/phase-gates.md` — this is the cursor: which phase we are in,
   the last validated step, and what is allowed next.
3. Read `docs/next-phases.md` — the plan for everything after Phase 8.
   It supersedes `project-prompt.md` §14.
4. Skim `docs/decisions/` (ADRs) for the "why". 0015, 0016 and 0017 shape
   everything currently in flight.
5. Read `docs/sessions/INDEX.md` only if you need history of a prior session.

Use the `session-protocol` skill for the full entry/exit checklist.

## How to pick a skill

Skills live in `.claude/skills/`. Each is one operation. Use the registry
at `.claude/skills/README.md` as the map. Quick routing:

- Closing out a phase (summarize → validate → STOP → confirm) → `phase-gate`
- Running the local stack, migrate/seed, smoke against localhost → `local-dev`
- Raw Terraform mechanics (fmt/validate/plan/apply, S3 state) → `tf-workflow`
- Full deploy orchestration (bootstrap, first local apply, OIDC, CI) → `deploy-stage`
- Destroying / stopping cost / post-demo cleanup → `teardown`
- Changing the FastAPI app, models, migrations, seed → `app-dev`
- Writing or adapting Playwright/DB tests → `test-dev`
- Adding or changing a skill itself → `skill-maintenance`
- Session entry/exit, committing the session summary → `session-protocol`

If unsure which skill fits, read `.claude/skills/README.md` before guessing.

## End of every session (do this last)

**Run `make session-close`.** It checks docs-check, that a summary dated today
exists and is linked from INDEX in both directions, that INDEX is in
chronological order, that the narrative's date matches the newest session, and
that nothing is left uncommitted or unpushed - then prints the Consequences of
any ADR this session added. The steps below are what it cannot do.

1. Run the relevant validation (see the skill you used).
2. Update `docs/phase-gates.md` if the phase status changed.
3. Write a session summary in `docs/sessions/` and add a row to
   `docs/sessions/INDEX.md`.
4. Record new architectural decisions as ADRs in `docs/decisions/`.
5. `git add` + `git commit` + `git push`. Work on the devbox is only shared
   once pushed.

See `session-protocol` for the exact steps and templates.

## Source of truth (do not duplicate state)

- Code, IaC, tests, docs, decisions → this git repo (GitHub is origin).
  This includes `docs/discussion-log.md`. The copy inside the Claude
  Project is a MIRROR that lags; never edit it, never reason from it
  without checking `git log` first.
- Infrastructure state → S3 Terraform state (not the chat, not local files).
- Run results / reports → GitHub Actions artifacts.
- Secrets → Secrets Manager / GitHub Secrets. Never committed.

Do NOT commit: `.env`, `*.tfstate`, secrets, raw chat transcripts, large logs.
