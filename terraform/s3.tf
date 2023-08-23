resource "aws_s3_bucket" "s3_bucket" {
  bucket        = "bucket-${local.name_alias}"
  force_destroy = var.is_development
}

resource "aws_s3_bucket" "s3_bucket_test" {
  bucket        = "bucket-v2-${local.name_alias}"
  force_destroy = var.is_development
}
