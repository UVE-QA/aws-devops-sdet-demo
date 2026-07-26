# ECR module: a single repository for the app image.
#
# force_delete defaults to FALSE. It was originally hardcoded to true so that a
# per-cycle `terraform destroy` could remove a repository still holding images
# (ADR-0011). Since ADR-0018 the registry lives at a permanent level that is
# never destroyed, where the flag's only remaining effect would be to make
# accidental image loss easier. Environments that genuinely own a throwaway
# repository can still opt in.

resource "aws_ecr_repository" "app" {
  name         = var.repository_name
  force_delete = var.force_delete

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name = var.repository_name
  }
}

# Bound storage on a registry that is never destroyed. Two rules, in priority
# order: untagged layers left behind by a re-push go quickly, then the tagged
# history is capped. A rule with tagStatus "any" must have the highest priority
# number, so it comes last.
resource "aws_ecr_lifecycle_policy" "app" {
  repository = aws_ecr_repository.app.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Expire untagged images after ${var.untagged_expire_days} day(s)"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = var.untagged_expire_days
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Keep last ${var.max_image_count} images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = var.max_image_count
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}
