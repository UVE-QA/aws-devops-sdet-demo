# Project Context Pointer — paste into Claude.ai Project Instructions

Append this block to the end of the Project Instructions. It orients every new
chat in the Project without re-pasting the full context.

---

## Project Context Pointer

- Repo: `aws-devops-sdet-demo`. Phase-gated (Phase 0-8), currently Phase 0.
- Tooling: Claude Code only (no Cowork). CC runs on the Lightsail devbox,
  accessed via VS Code Remote-SSH (preferred) or bare SSH.
- Source of truth for decisions: `docs/discussion-log.md` and `docs/decisions/`
  in the Project files (and in git once on the devbox).
- The full build prompt is `docs/project-prompt.md` (in Project files).
- Key invariants: dedicated AWS Organizations demo member account; GitHub OIDC
  (no static keys); S3 Terraform remote state; DB password in Secrets Manager;
  no NAT / no EKS in v0; single app container (FastAPI + ALB + ECS Fargate +
  RDS); repeatable deploy -> demo -> destroy lifecycle.
- Language: all prompts/instructions/skills in English; discussion may be in
  Russian. Skill trigger words include Russian synonyms.
- New chat ritual: read this pointer, then the Project files for full context.
  Do not rely on auto-generated Memory as the source of truth.
