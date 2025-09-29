terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }

  }
  required_version = ">= 1.5.4"
}

provider "aws" {
  region  = "eu-west-1"
  profile = null
}

output "output_rds_host" {
  value = aws_db_instance.rds.address
}

output "output_rds_password" {
  value     = random_password.rds_password.result
  sensitive = true
}

output "rest_api_url" {
  value = aws_api_gateway_deployment.api_deployment.invoke_url
}

data "aws_caller_identity" "current" {}

locals {
  name_alias    = replace(terraform.workspace, "_", "-")
  database_name = "database"
  account_id    = data.aws_caller_identity.current.account_id
}

variable "is_development" {
  description = "Variable to flag whether bucket should be deleted with content; by default False"
  type        = bool
  default     = false
}

variable "rest_api_name" {
  type        = string
  description = "Name of the API Gateway created"
  default     = "rest_api"
}

variable "region_aws" {
  type        = string
  description = "Name of the region"
  default     = "eu-west-1"
}

variable "rds_database_name" {
  type        = string
  description = "Name of the database"
  default     = "database_rds"
}