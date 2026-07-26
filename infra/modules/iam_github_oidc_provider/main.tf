# GitHub OIDC identity provider — the trust anchor, on its own.
#
# Split out of the former iam_github_oidc module (ADR-0021). AWS allows exactly
# ONE OpenID Connect provider per issuer URL per account, while the project
# needs one deploy role PER ENVIRONMENT. Instantiating the old combined module
# twice would have failed with EntityAlreadyExists on this resource.
#
# This module is applied once per account, locally under demo-admin, and is
# never destroyed by an environment teardown (ADR-0015).

resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [var.thumbprint]

  tags = {
    Name = "${var.name_prefix}-github-oidc"
  }
}
