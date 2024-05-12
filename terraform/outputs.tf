output "output_rds_host" {
  value = aws_db_instance.rds.address
}

output "output_rds_password" {
  value     = random_password.rds_password.result
  sensitive = true
}

output "output_security_group_id" {
  value = aws_security_group.epc_security_endpoints.id
}

output "output_public_subnets" {
  value = module.vpc.public_subnets
}

output "parameter_rds_password" {
  value = aws_ssm_parameter.rds_password_parameter.name
}