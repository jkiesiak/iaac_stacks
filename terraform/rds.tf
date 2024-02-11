resource "aws_db_instance" "rds" {
  allocated_storage = "50"
  storage_type      = "gp2"
  storage_encrypted = true
  engine            = "postgres"
  # https://docs.aws.amazon.com/AmazonRDS/latest/PostgreSQLReleaseNotes/postgresql-versions.html#postgresql-versions-version153
  engine_version                        = "15.5"
  instance_class                        = "db.t3.micro"
  identifier                            = local.name_alias
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
  #  monitoring_interval                   = 30
  vpc_security_group_ids = [aws_security_group.security_group.id]
  db_subnet_group_name   = aws_db_subnet_group.rds_subnets_group.id

  depends_on = [aws_vpc.my_vpc]
}

resource "random_password" "rds_password" {
  length           = 16
  special          = true
  override_special = "!#$%&*-_=+[]{}<>:?"
}

resource "aws_ssm_parameter" "rds_password_parameter" {
  name  = "/rds_password-${local.name_alias}"
  type  = "SecureString"
  value = random_password.rds_password.result

  tags = {
    Terraform   = "true"
    Environment = "production"
  }
}

resource "null_resource" "rds_setup" {
  provisioner "local-exec" {
    command = "psql --echo-queries -h \"${aws_db_instance.rds.address}\" -U postgres -f schema.sql "
    environment = {
      PGPASSWORD = nonsensitive(random_password.rds_password.result)
    }
  }
  triggers = {
    always_run = "${timestamp()}"
  }
}

resource "aws_db_subnet_group" "rds_subnets_group" {
  name        = "${local.name_alias}-rds"
  description = "RDS subnet group for Magic Star RDS containing public subnets."
  subnet_ids  = [aws_subnet.subnet_public_v1.id, aws_subnet.subnet_public_v2.id]
}

