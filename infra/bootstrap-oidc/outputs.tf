output "oidc_provider_arn" {
  description = "ARN of the GitHub OIDC identity provider (one per account)."
  value       = module.oidc_provider.arn
}

output "stage_deploy_role_arn" {
  description = "Deploy role for stage. Set as the OIDC_ROLE_ARN variable on the GitHub Environment 'stage'."
  value       = module.deploy_role_stage.deploy_role_arn
}

output "prod_deploy_role_arn" {
  description = "Deploy role for prod. Set as the OIDC_ROLE_ARN variable on the GitHub Environment 'prod'. Assumable ONLY through that environment, so it cannot be used without reviewer approval."
  value       = module.deploy_role_prod.deploy_role_arn
}
