# ADR-0016: Destroy the ALB in a targeted pass before the network

## Status
Accepted (Phase 8). Complements ADR-0015; corrects part of its Context.

## Context
The first destroy.yml run that got past the C2 self-deletion bug still failed,
after ~20 minutes, on:

  Error: deleting EC2 Internet Gateway (igw-...): detaching ... from VPC
  (vpc-...): DependencyViolation: Network vpc-... has some mapped public
  address(es). Please unmap those public address(es) before detaching the
  gateway.

Cause: there is NO dependency edge between module.alb and the IGW in
module.network. The ALB depends on the public subnets and its security group;
the IGW depends only on the VPC. Terraform therefore destroys them
CONCURRENTLY. The ALB's ENIs still hold mapped public IPs, and the IGW cannot
be detached while they exist. Terraform retried the detach until it gave up.

The race is nondeterministic. A local destroy of the exact same graph succeeded:
both the IGW and the ALB reported "Destruction complete after 27s" — the ALB
released its ENIs just inside the IGW retry budget. This is why the bug hid for
so long and why it looked like an infrastructure flake rather than a graph defect.

Correction to earlier analysis: the Phase-7 destroy #3 failure on
ec2:DetachInternetGateway was recorded as a consequence of the deploy role
deleting its own permissions. This run reproduced the identical failure with the
role's permissions fully intact, so that failure was — at least in part — this
ordering race, not permission loss. ADR-0015 remains valid on its own terms:
self-deletion was real, proven, and separately fixed.

Two smaller defects surfaced in the same run:
- iam:ListInstanceProfilesForRole was missing from IamManageScoped. The AWS
  provider calls it while deleting ANY IAM role, so both ECS role deletions
  failed with AccessDenied. It was lost when C2 narrowed the statement.
- eks:ListClusters was missing, so the workflow's own "no EKS in v0" assertion
  could not run: the policy was too narrow to verify the absence of the very
  thing it forbids creating.

## Decision
1. destroy.yml runs `terraform destroy -target=module.alb` as a separate step
   BEFORE the full destroy. A targeted destroy also removes everything that
   depends on the target, so module.ecs (depends_on = [module.alb]) is torn
   down first and its task ENIs are released as well. Only then does the full
   destroy reach the network, by which time no mapped public addresses remain.
2. Add iam:ListInstanceProfilesForRole to IamManageScoped, still scoped to
   exactly the two ECS role ARNs.
3. Add a separate read-only statement TeardownVerifyRead with eks:ListClusters.
   Kept separate from InfraManage so the intent — verification, not management —
   is explicit.

## Alternatives rejected
- depends_on from the IGW to the ALB: circular, since the ALB needs the VPC and
  subnets. Expressing it would require passing an ALB reference into the network
  module behind a terraform_data marker (depends_on does not accept variable
  values). More indirection than the pipeline-level ordering, and invisible to
  anyone reading the workflow.
- Raising the IGW delete timeout: widens the window, does not fix the ordering,
  and the failure would still be nondeterministic.
- Moving tasks to private subnets: requires NAT or VPC endpoints, contradicting
  ADR-0006 (no NAT in v0).

## Consequences
- Teardown via Actions is deterministic. destroy #7: green end-to-end, 8m21s.
- The targeted pass costs ~7.5 min (ALB deletion dominates), but that time was
  previously spent losing IGW retries anyway.
- destroy.yml now issues two terraform destroy commands; the second finds
  module.alb and module.ecs already gone and proceeds to the rest.
- The Phase-7 caveat about -target still applies: a targeted run does not
  reconcile the rest of the configuration. Acceptable here because the full
  destroy runs immediately afterwards.
