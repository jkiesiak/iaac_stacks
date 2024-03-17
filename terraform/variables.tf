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