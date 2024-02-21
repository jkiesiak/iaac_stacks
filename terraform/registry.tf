resource "aws_ecr_repository" "my_repository" {
  name                 = "docker/${local.name_alias}"
  image_tag_mutability = "MUTABLE"
  force_delete         = true


  image_scanning_configuration {
    scan_on_push = true
  }
  # Uncomment to apply tags
  /*
  tags = {
    Environment = "development"
  }
  */
}

output "repository_url" {
  value = aws_ecr_repository.my_repository.repository_url
}

output "repository_name" {
  value = aws_ecr_repository.my_repository.name
}