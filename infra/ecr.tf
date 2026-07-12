# One image repository. api and worker run the SAME image with different
# commands (uvicorn vs procrastinate worker), so one repo is enough.

resource "aws_ecr_repository" "api" {
  name = "${var.project}-api"

  image_tag_mutability = "MUTABLE" # :staging is a moving tag; shas are immutable in practice

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "api" {
  repository = aws_ecr_repository.api.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep only the 20 most recent images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 20
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}
