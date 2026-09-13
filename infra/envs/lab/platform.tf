# What Terraform puts INTO the cluster (ADR-0097): the platform, not the
# application. The application is the Helm chart the workflow installs with
# the digests stage tested (plan item 3); this file is what has to be there
# before that install can succeed - the namespace, the database secret, and
# the controller that turns an Ingress into a load balancer.

# --- the namespace and the secret -------------------------------------------

resource "kubernetes_namespace_v1" "demo" {
  metadata {
    name = module.eks.namespace
    labels = {
      "app.kubernetes.io/part-of" = "aws-devops-sdet-demo"
    }
  }

  depends_on = [module.eks]
}

# The same secret the ECS task definitions inject (ADR-0005), read once at
# apply and written as a Kubernetes Secret the chart mounts as DATABASE_URL.
# It passes through Terraform's state, which already holds the password the
# RDS module generated; nothing here is a second copy of a credential that
# was not in state before.
data "aws_secretsmanager_secret_version" "db" {
  secret_id = module.rds.db_secret_arn

  # The secret's VALUE is written after the instance exists - the URL holds
  # its address - while its ARN is known at once. Without this the read
  # starts beside the RDS create and retries for the eight minutes it takes,
  # which the first local apply showed as `Still reading… [02m20s]`.
  depends_on = [module.rds]
}

resource "kubernetes_secret_v1" "db" {
  metadata {
    name      = "db-credentials"
    namespace = kubernetes_namespace_v1.demo.metadata[0].name
  }

  data = {
    DATABASE_URL = jsondecode(data.aws_secretsmanager_secret_version.db.secret_string).url
  }
}

# --- the AWS Load Balancer Controller ---------------------------------------
#
# Installed by Terraform because it is platform: the chart the workflow
# installs would otherwise wait on a controller nobody had put there. The
# chart version and the IAM policy vendored in modules/eks are from the same
# controller release and are bumped together.
#
# DEFAULT TAGS ARE THE SWEEP'S EYES. The balancer an Ingress creates is
# tagged by the controller and by nobody else; without Project and
# Environment on it, `sweep-orphans.sh` - which asks the tagging API for
# exactly those - could not see the one resource in this environment that
# Terraform does not own. That is the teardown trap the plan named.

resource "helm_release" "alb_controller" {
  name       = "aws-load-balancer-controller"
  repository = "https://aws.github.io/eks-charts"
  chart      = "aws-load-balancer-controller"
  version    = var.alb_controller_chart_version
  namespace  = "kube-system"

  atomic          = true
  wait            = true
  timeout         = 600
  cleanup_on_fail = true

  set {
    name  = "clusterName"
    value = module.eks.cluster_name
  }
  set {
    name  = "region"
    value = var.region
  }
  set {
    name  = "vpcId"
    value = module.network.vpc_id
  }
  set {
    name  = "serviceAccount.create"
    value = "true"
  }
  set {
    name  = "serviceAccount.name"
    value = module.eks.controller_service_account
  }
  set {
    name  = "serviceAccount.annotations.eks\\.amazonaws\\.com/role-arn"
    value = module.eks.controller_role_arn
  }
  set {
    name  = "defaultTags.Project"
    value = "aws-devops-sdet-demo"
  }
  set {
    name  = "defaultTags.Environment"
    value = var.environment
  }
  set {
    name  = "defaultTags.ManagedBy"
    value = "aws-load-balancer-controller"
  }

  depends_on = [module.eks]
}
