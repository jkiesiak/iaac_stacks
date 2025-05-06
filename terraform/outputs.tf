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