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
- Terraform remote state in S3 (`infra/bootstrap` creates the bucket once).
- DB password via Secrets Manager, never in repo.
- No NAT Gateway, no EKS in v0.

## Start of every session (do this first)

1. `git pull` to get the current source of truth.
2. Read `docs/phase-gates.md` — this is the cursor: which phase we are in,
   the last validated step, and what is allowed next.
3. Skim `docs/decisions/` (ADRs) for the "why" behind the architecture.
4. Read `docs/sessions/INDEX.md` only if you need history of a prior session.

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
- Infrastructure state → S3 Terraform state (not the chat, not local files).
- Run results / reports → GitHub Actions artifacts.
- Secrets → Secrets Manager / GitHub Secrets. Never committed.

Do NOT commit: `.env`, `*.tfstate`, secrets, raw chat transcripts, large logs.
