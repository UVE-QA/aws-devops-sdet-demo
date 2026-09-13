# The cluster, and only the cluster (ADR-0095). It used to be one module with
# the security group, the roles, the task definition and the service, which was
# the right shape for one service and the wrong one for two: instantiated twice
# it would have made two clusters and two sets of roles, and a cluster is the
# room the services run in, not a property of either. Everything per service is
# in modules/ecs-service.

resource "aws_ecs_cluster" "this" {
  name = "${var.name_prefix}-cluster"

  setting {
    name  = "containerInsights"
    value = "disabled"
  }

  tags = {
    Name = "${var.name_prefix}-cluster"
  }
}
