resource "aws_db_instance" "rds" {
  allocated_storage                     = "50"
  storage_type                          = "gp2"
  storage_encrypted                     = true
  engine                                = "postgres"
  engine_version                        = "15.5"
  instance_class                        = "db.t3.micro"
  identifier                            = "rds-database-${local.name_alias}"
  username                              = "postgres"
  password                              = random_password.rds_password.result
  skip_final_snapshot                   = var.is_development
  auto_minor_version_upgrade            = false
  backup_retention_period               = 7
  enabled_cloudwatch_logs_exports       = ["postgresql"]
  iam_database_authentication_enabled   = true
  maintenance_window                    = "Wed:04:06-Wed:04:36"
  deletion_protection                   = !var.is_development
  performance_insights_enabled          = true
  performance_insights_retention_period = 7
  publicly_accessible                   = true
  copy_tags_to_snapshot                 = true
  multi_az                              = true
  vpc_security_group_ids                = [aws_security_group.rds_security_group.id]
  db_subnet_group_name                  = aws_db_subnet_group.rds_subnet_group.name

  depends_on = [module.vpc]
}

resource "random_password" "rds_password" {
  length           = 16
  special          = true
  override_special = "!#$%&*-_=+[]{}<>:?"
}

resource "aws_secretsmanager_secret" "rds_password_secret" {
  name = "rds-password-${local.name_alias}"

  description = "RDS password for ${local.name_alias}"

  tags = {
    Terraform   = "true"
    Environment = "production"
  }
}

resource "aws_secretsmanager_secret_version" "rds_password_secret_version" {
  secret_id = aws_secretsmanager_secret.rds_password_secret.id
  secret_string = jsonencode({
    password = random_password.rds_password.result
  })
}

resource "null_resource" "rds_apply_schema_setup" {
  provisioner "local-exec" {
    command = "psql --echo-queries -h \"${aws_db_instance.rds.address}\" -U postgres -f sql_schema/schema.sql"
    environment = {
      PGPASSWORD = nonsensitive(random_password.rds_password.result)
    }
  }
  triggers = {
    always_run = "${timestamp()}"
  }
}