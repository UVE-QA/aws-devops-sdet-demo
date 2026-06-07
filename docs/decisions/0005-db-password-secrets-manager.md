# ADR-0005: DB password generated and stored in Secrets Manager

## Status
Accepted (Phase 0)

## Context
The RDS master password must never appear in the repository, tfvars, Terraform
outputs, or container plaintext environment variables. It must still be
available to the ECS task at runtime and reproducible across deploy/destroy
cycles.

## Decision
Generate the RDS master password with the Terraform `random_password` resource
and store the connection details in AWS Secrets Manager. The ECS task reads the
secret via the task definition `secrets` block (`valueFrom` = secret ARN), not
via plaintext `environment`. Relevant Terraform values are marked `sensitive`.

## Decision details
- Secret holds the DB connection details (username, password, host, port,
  dbname) or the full DATABASE_URL.
- ECS execution role gets `secretsmanager:GetSecretValue` scoped to the secret
  ARN only.
- Outputs may expose the secret ARN (`db_secret_arn`) but never the value.
- `recovery_window_in_days = 0` so the secret name is not reserved after delete
  (see ADR-0011 for the repeatability rationale).

## Consequences
- No DB password in repo, tfvars, outputs, or plaintext env.
- The password is regenerated on each fresh apply; nothing to rotate by hand
  for the demo.
- Reading the secret requires the IGW egress path from the public subnet (see
  ADR-0006), since there is no NAT or VPC endpoint in v0.
