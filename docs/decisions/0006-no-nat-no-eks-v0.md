# ADR-0006: No NAT Gateway and no EKS in v0

## Status
Accepted (Phase 0)

## Context
A typical "production" pattern puts workloads in private subnets behind a NAT
Gateway and may use EKS for orchestration. Both add real cost and complexity: a
NAT Gateway bills hourly plus per-GB, and EKS adds a control-plane fee and
significant operational surface. This is a cost-conscious, periodically
torn-down demo where neither is justified for v0.

## Decision
v0 uses neither a NAT Gateway nor EKS. The single Fargate task runs in a PUBLIC
subnet with `assign_public_ip = true`, reaching ECR, Secrets Manager, and
CloudWatch over the Internet Gateway. Orchestration is ECS Fargate, not EKS.

## Decision details
- Network: VPC with 2 public subnets (app) + 2 private DB subnets (RDS), IGW,
  public route table. No NAT.
- App inbound is restricted to the ALB security group only; RDS inbound is
  restricted to the ECS security group only. Public IP is for egress, not open
  ingress.
- RDS stays private (`publicly_accessible = false`); only the app reaches it.

## Consequences
- Significant cost savings (no NAT hourly/data charges, no EKS control plane).
- Trade-off: the app task has a public IP. This is acceptable for a demo
  because ingress is locked to the ALB SG, but it is documented as a v0
  simplification.
- If the task is ever moved to a private subnet (a Phase 8 option), a NAT
  Gateway or VPC endpoints become mandatory for ECR/Secrets/Logs egress.
- EKS/Helm/ArgoCD remain explicitly deferred to later phases.
