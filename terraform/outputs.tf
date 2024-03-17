output "output_sqs_queue" {
  value = aws_batch_job_queue.sample_job_queue.name
}

output "output_s3_input_bucket" {
  value = aws_s3_bucket.s3_bucket.id
}

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