# ADR-0021: The OIDC provider is split from the deploy role, and prod's role has no branch subject

## Status
Accepted (Phase 9.1). Refines ADR-0003 and ADR-0015; implements the second
deploy role required by ADR-0017 D1.

## Context

`infra/bootstrap-oidc` instantiated a single module, `iam_github_oidc`, which
created **both** the GitHub OpenID Connect identity provider and the Actions
deploy role. With one environment that shape was invisible.

Phase 9.1 needs a second deploy role, for prod, in the same account. Copying the
module block would not have produced one:

```text
AWS allows exactly ONE OIDC provider per issuer URL per account.
A second instance fails on aws_iam_openid_connect_provider with
EntityAlreadyExists.
```

This is the project's recurring failure mode rather than a new one. The module
was correct for every path ever exercised, and wrong for the first path that had
never been run — the same shape as ADR-0015, ADR-0016, and the four defects found
in Phase 9.0. It was found by reading the resource, not by an error, because
nothing had yet tried to apply it.

The second question surfaced with it. ADR-0017 makes prod's approval gate a
GitHub Environment with required reviewers. The existing trust policy grants:

```text
repo:<owner>/<repo>:ref:refs/heads/main
```

A subject of that form is satisfied by **any** workflow running on `main`. Had
prod's role been created from the same template, an unreviewed workflow on the
default branch could assume it and apply to prod, and the reviewers would never
have been consulted. The approval gate would have been real in the GitHub UI and
absent in IAM.

## Decision

**Two modules.**

```text
infra/modules/iam_github_oidc_provider   the provider. One per account.
infra/modules/iam_github_deploy_role     the role + policy. One per environment.
```

The role module takes `oidc_provider_arn` as an input and creates no provider,
so it can be instantiated as many times as there are environments.
`infra/bootstrap-oidc` now holds one `oidc_provider` and two roles,
`deploy_role_stage` and `deploy_role_prod`.

**Prod's role trusts only the environment subject.**

The role module gains `trust_branch_ref` (default `true`). Stage keeps `true`.
Prod sets `false`, so its only trust subject is
`repo:<owner>/<repo>:environment:prod`. The role becomes unassumable except
through the reviewer-gated environment. An empty resulting subject list is
rejected by a `precondition` rather than silently producing a trust policy
nothing can satisfy.

**Both roles stay scoped by `name_prefix`.**

Every resource-scoped statement — state bucket, DB secret pattern, the two ECS
roles — derives from `name_prefix`, so the stage role grants nothing over prod
resources and vice versa. That was already true; instantiating twice is what
makes it load-bearing.

**The refactor moves state, it does not rebuild it.**

The provider and stage role exist in AWS today. `moved` blocks in
`infra/bootstrap-oidc/main.tf` rename them in state. No `terraform state mv` is
run by hand.

## Consequences

- The next local apply of `infra/bootstrap-oidc` under `demo-admin` **must plan
  as: 1 role and 1 role policy added, 0 destroyed.** Anything else means a
  `moved` block is wrong. Do not apply through it: recreating the provider
  invalidates the stage role's trust and breaks a working stage cycle to fix a
  prod one.
- `bootstrap-oidc` no longer takes a `name_prefix` variable. Prefixes are derived
  from the same project literal the environments hardcode, so the alignment the
  old default silently depended on is now structural.
- Outputs are renamed to `stage_deploy_role_arn` and `prod_deploy_role_arn`.
  Nothing consumes them programmatically — the GitHub Environment variables are
  set by hand — but the old singular name would now be ambiguous.
- `destroy.yml` can finally offer prod for real: the role its dropdown implied
  since Phase 8 exists after the next apply. Wiring it is 9.1 work and is not
  done by this ADR.
- Prod's role cannot be used for a break-glass manual run from a branch. That is
  intentional. Break-glass is `demo-admin` over SSO, which is audited and human.

## Rejected

- **A `create_oidc_provider` flag on the combined module.** Rejected: a module
  that creates a different set of resources depending on a boolean has to be
  read twice to know what it does, and the flag would have to be false for
  exactly one instance for reasons living outside the module.
- **A separate OIDC provider per environment.** Not available; AWS forbids it.
  Worth recording, because it is the shape someone will reach for first.
- **Reusing one role for both environments with a wider trust policy.** Rejected:
  it deletes the blast-radius boundary that `name_prefix` scoping provides, and
  stage credentials reaching prod is exactly what ADR-0017 D1 rules out.
