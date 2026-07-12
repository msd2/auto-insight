provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "auto-insight"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
