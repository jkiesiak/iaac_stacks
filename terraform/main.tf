terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.16"
    }

  }
  required_version = ">= 1.2.0"
}

variable "access_key" {
  type    = string
  default = "default_value"
}

variable "secret_key" {
  type    = string
  default = "default_value"
}

provider "aws" {
  region     = "eu-west-1"
  access_key = var.access_key
  secret_key = var.secret_key
}

