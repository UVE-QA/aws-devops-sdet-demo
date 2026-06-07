# ECR module: a single repository for the app image. force_delete = true so a
# `terraform destroy` removes the repo even when it still holds pushed images
# (ADR-0011) — otherwise the destroy fails on a non-empty repo and leaves
# clutter/cost across the repeatable deploy/destroy cycle.

resource "aws_ecr_repository" "app" {
  name         = var.repository_name
  force_delete = true

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name = var.repository_name
  }
}

# Keep only the most recent images to cap storage cost across cycles.
resource "aws_ecr_lifecycle_policy" "app" {
  repository = aws_ecr_repository.app.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
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
