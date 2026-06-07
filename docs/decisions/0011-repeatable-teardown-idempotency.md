# ADR-0011: Repeatable teardown and re-apply idempotency

## Status
Accepted (Phase 0)

## Context
The environment is brought up, demoed, then destroyed repeatedly to avoid
ongoing cost. Several AWS resources leave residue that blocks the NEXT apply or
keeps billing after a destroy: non-empty ECR repos block deletion, deleted
Secrets Manager secrets reserve their name for a recovery window, RDS leaves
final snapshots and automated backups, and ECS auto-created log groups linger.

## Decision
Make every deploy -> demo -> destroy -> deploy cycle clean and idempotent via:
- ECR `force_delete = true` (destroy removes the repo even with images).
- Secrets Manager `recovery_window_in_days = 0` (name freed immediately, no
  "already scheduled for deletion" on the next apply).
- RDS `skip_final_snapshot = true` and `backup_retention_period = 0` (no
  leftover snapshots/backups).
- CloudWatch log group Terraform-managed (not ECS auto-created) so destroy
  actually removes it; short `log_retention_days` for stage.
- No hardcoded global-unique names that linger after delete.

## Consequences
- A fresh `terraform apply` after a destroy succeeds with no name conflicts.
- Nothing billable survives a destroy EXCEPT the Terraform state bucket
  (ADR-0004), which is intentionally retained at near-zero cost.
- These settings are demo-appropriate and deliberately NOT production-safe
  (no final snapshot, no backups); production would revisit them.
- A required Budgets alert and a destroy-time verification step back this up
  against a forgotten teardown (Budgets is configured in the env, not an ADR).
