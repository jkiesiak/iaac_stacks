locals {
  name_alias = "joanna-pipeline"
}

resource "aws_s3_bucket" "s3_bucket" {
  bucket = "bucket-${local.name_alias}"
}

resource "aws_s3_bucket" "s3_bucket_test" {
  bucket = "bucket-${local.name_alias}-v2"
}

resource "aws_vpc" "vpc_mine" {
  cidr_block       = "10.0.0.0/16"
  instance_tenancy = "default"

  tags = {
    Name = "main"
  }
}