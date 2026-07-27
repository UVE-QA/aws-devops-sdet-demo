#!/usr/bin/env bash
# Observe what an environment ACTUALLY has in AWS, and print it as JSON.
#
# This is the second of the dashboard's two sources (ADR-0026). It exists
# because GitHub Actions cannot answer the question it looks like it answers: a
# green `destroy` run is a statement about a workflow, not about an account.
# Something can be recreated after the run ended, or removed by hand, and the
# run would say the same thing either way.
#
# So the rule this script obeys, and the reason it is separate from the upload:
#   it reports ONLY what it just read from the AWS API,
#   every field it could not read is null, never a plausible default,
#   and it says nothing whatsoever about the run that invoked it.
#
# Run with the DEPLOY role's credentials - it needs ecs/elbv2/rds reads, which
# that role already has (ecs:*, elasticloadbalancing:*, rds:* in
# iam_github_deploy_role). The upload then happens under the narrow publish
# role, in a separate step: a role that can change infrastructure has no
# business writing the page that reports on it.
#
# Usage:
#   scripts/observe-environment.sh <environment> > status.json
#
# Environment:
#   AWS_REGION  required
#   APP_URL     optional. Known only while the environment is up, because it
#               comes from a Terraform output; absent during a teardown.
set -euo pipefail

env_name="${1:?usage: observe-environment.sh <environment>}"
: "${AWS_REGION:?AWS_REGION is not set}"

prefix="aws-devops-sdet-demo-${env_name}"
app_url="${APP_URL:-}"

# Fail loudly, here, if the credentials are gone. A post-teardown check whose
# token had expired once printed empty lists for every resource, which is
# exactly what a clean account looks like; this project has already been fooled
# by that once and will not be again.
account="$(aws sts get-caller-identity --query Account --output text)"

# ---- load balancer ---------------------------------------------------------
alb="$(aws elbv2 describe-load-balancers --region "$AWS_REGION" \
  --query "LoadBalancers[?starts_with(LoadBalancerName, '${prefix}')] | [0].{name:LoadBalancerName,dns_name:DNSName,state:State.Code}" \
  --output json)"

# ---- ecs cluster and service ----------------------------------------------
cluster_arn="$(aws ecs list-clusters --region "$AWS_REGION" \
  --query "clusterArns[?contains(@, '${prefix}')] | [0]" --output text)"

service='null'
image='null'
if [ "$cluster_arn" != "None" ] && [ -n "$cluster_arn" ]; then
  service_arn="$(aws ecs list-services --region "$AWS_REGION" --cluster "$cluster_arn" \
    --query "serviceArns[0]" --output text)"
  if [ "$service_arn" != "None" ] && [ -n "$service_arn" ]; then
    service="$(aws ecs describe-services --region "$AWS_REGION" \
      --cluster "$cluster_arn" --services "$service_arn" \
      --query "services[0].{name:serviceName,status:status,desired:desiredCount,running:runningCount}" \
      --output json)"
    task_def="$(aws ecs describe-services --region "$AWS_REGION" \
      --cluster "$cluster_arn" --services "$service_arn" \
      --query "services[0].taskDefinition" --output text)"
    if [ "$task_def" != "None" ] && [ -n "$task_def" ]; then
      # The image reference prod runs is a DIGEST, because promotion resolves it
      # from the tag stage tested (promote-prod.yml). Printing it is what lets a
      # viewer check that prod is running the exact bytes stage tested, rather
      # than being told so.
      image="$(aws ecs describe-task-definition --region "$AWS_REGION" \
        --task-definition "$task_def" \
        --query "taskDefinition.containerDefinitions[0].image" --output json)"
    fi
  fi
fi

# ---- database -------------------------------------------------------------
rds="$(aws rds describe-db-instances --region "$AWS_REGION" \
  --query "DBInstances[?starts_with(DBInstanceIdentifier, '${prefix}')] | [0].{identifier:DBInstanceIdentifier,status:DBInstanceStatus}" \
  --output json)"

# ---- state ----------------------------------------------------------------
# Three observations, three answers, and "partial" is a real one: a half-torn-down
# environment is the state this project has actually been in, twice, and calling
# it either "up" or "destroyed" would have hidden it.
#
# `if ...; then` and not `[ ... ] && present=$((present+1))`: under `set -e` the
# short-circuit form aborts the script the moment a test is FALSE, which is
# precisely the "this resource is gone" case this function exists to count. The
# first version of this file had that bug and would have failed every time it
# was run against a torn-down environment - the one state the dashboard most
# needs to report.
present=0
for observation in "$alb" "$service" "$rds"; do
  if [ "$(jq -r 'if . == null then "0" else "1" end' <<<"$observation")" = "1" ]; then
    present=$((present + 1))
  fi
done

case "$present" in
  0) state="destroyed" ;;
  3) state="up" ;;
  *) state="partial" ;;
esac

jq -n \
  --arg environment "$env_name" \
  --arg state "$state" \
  --arg account "$account" \
  --arg region "$AWS_REGION" \
  --arg observed_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --arg app_url "$app_url" \
  --argjson load_balancer "$alb" \
  --argjson ecs_service "$service" \
  --argjson db_instance "$rds" \
  --argjson image "$image" \
  '{
     schema: 1,
     environment: $environment,
     state: $state,
     observed_at: $observed_at,
     account: $account,
     region: $region,
     app_url: (if $app_url == "" then null else $app_url end),
     image: $image,
     resources: {
       load_balancer: $load_balancer,
       ecs_service: $ecs_service,
       db_instance: $db_instance
     }
   }'
