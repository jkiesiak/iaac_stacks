locals {
  name_alias    = "joanna-pipeline"
  database_name = "database"
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
