#!/usr/bin/env bash
#
# Install the application on the lab (ADR-0097 D3): the same three digests
# stage tested, resolved from the registries by ONE tag, onto the cluster
# infra/envs/lab made - with `--atomic --wait`, so a release that does not
# come up is rolled back rather than left half-there. Then wait for the
# Ingress to have a hostname and for that hostname to answer /health, and
# print it: that is the URL the suites run against.
#
# Used by the lab job in the cycle and by hand on the devbox; both read the
# environment's outputs from Terraform rather than repeating them.
#
# Usage:  IMAGE_TAG=<git sha> scripts/lab-install.sh
#         scripts/lab-install.sh --uninstall      # and wait for the balancer to go
#
# Credentials: whatever `aws` finds - the deploy role in CI, demo-admin here.

set -euo pipefail

REGION="${AWS_REGION:-us-west-2}"
ENV_DIR="infra/envs/lab"
RELEASE="demo"
REPOS=(api:aws-devops-sdet-demo-app web:aws-devops-sdet-demo-web worker:aws-devops-sdet-demo-worker)

out() { terraform -chdir="$ENV_DIR" output -raw "$1"; }

cluster="$(out cluster_name 2>/dev/null || true)"
if [ -z "$cluster" ]; then
  if [ "${1:-}" = "--uninstall" ]; then
    echo "no cluster in the lab's state - nothing to uninstall, and no balancer to wait for"
    exit 0
  fi
  echo "::error::the lab's state has no cluster - apply infra/envs/lab first" >&2
  exit 1
fi
namespace="$(out namespace)"
aws eks update-kubeconfig --region "$REGION" --name "$cluster" >/dev/null

if [ "${1:-}" = "--uninstall" ]; then
  # THE TEARDOWN TRAP (ADR-0097 D6). The chart's Ingress is a load balancer
  # Terraform does not own; uninstalling the chart asks the controller to
  # delete it, and `terraform destroy` must not reach the VPC before it has.
  # So this waits for the balancer to be GONE from AWS, not for helm to
  # return - helm returns when the Ingress object is deleted, which is the
  # request, not the deletion.
  name="aws-devops-sdet-demo-lab-alb"
  helm uninstall "$RELEASE" -n "$namespace" --wait --timeout 5m 2>/dev/null || echo "no release to uninstall"
  for _ in $(seq 1 60); do
    if ! aws elbv2 describe-load-balancers --region "$REGION" --names "$name" >/dev/null 2>&1; then
      echo "the controller's balancer is gone"; exit 0
    fi
    sleep 5
  done
  echo "::error::the balancer $name is still there five minutes after the uninstall - terraform destroy would fail on the VPC"
  exit 1
fi

tag="${IMAGE_TAG:?set IMAGE_TAG to the commit whose images stage tested}"
sets=()
for entry in "${REPOS[@]}"; do
  svc="${entry%%:*}"; repo="${entry#*:}"
  url="$(aws ecr describe-repositories --region "$REGION" --repository-names "$repo" \
           --query 'repositories[0].repositoryUri' --output text)"
  digest="$(aws ecr describe-images --region "$REGION" --repository-name "$repo" \
              --image-ids imageTag="$tag" --query 'imageDetails[0].imageDigest' --output text 2>/dev/null || true)"
  if [ -z "$digest" ] || [ "$digest" = "None" ]; then
    echo "::error::tag '$tag' is not in $repo - the lab runs what stage tested, and stage has not pushed this" >&2
    exit 1
  fi
  echo "$svc: $url@$digest"
  sets+=(--set "images.$svc.repository=$url" --set "images.$svc.digest=$digest")
done

helm upgrade --install "$RELEASE" charts/demo \
  --namespace "$namespace" \
  --atomic --wait --timeout 10m \
  "${sets[@]}" \
  --set "itemsQueueUrl=$(out items_queue_url)" \
  --set "dbSecretName=$(out db_secret_name)" \
  --set "serviceAccounts.api.roleArn=$(out api_role_arn)" \
  --set "serviceAccounts.worker.roleArn=$(out worker_role_arn)"

# The hostname arrives on the Ingress status once the controller has built
# the balancer; the balancer answers once its targets are healthy. Two waits,
# because the first says nothing about the second.
host=""
for _ in $(seq 1 60); do
  host="$(kubectl get ingress "$RELEASE" -n "$namespace" -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || true)"
  [ -n "$host" ] && break
  sleep 5
done
if [ -z "$host" ]; then
  echo "::error::the Ingress has no hostname after five minutes - the controller did not build the balancer (kubectl -n kube-system logs deploy/aws-load-balancer-controller)" >&2
  exit 1
fi
echo "ingress: http://$host"
for _ in $(seq 1 60); do
  if curl -sf -o /dev/null "http://$host/health"; then
    echo "lab_url=http://$host"
    exit 0
  fi
  sleep 5
done
echo "::error::http://$host/health did not answer 200 within five minutes of the hostname appearing" >&2
exit 1
