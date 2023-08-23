module "db" {
  source = "terraform-aws-modules/rds/aws"

  identifier = "demodb-${local.name_alias}"

  engine               = "postgres"
  engine_version       = "14"
  family               = "postgres14"
  major_engine_version = "14"
  instance_class       = "db.t4g.large"

  allocated_storage     = 20
  max_allocated_storage = 100

  db_name  = "PostgreSql1"
  username = "postgres1"
  password = random_password.rds_password.result

  port = 5432

  iam_database_authentication_enabled = true
  #  db_subnet_group_name   = module.vpc.database_subnet_group
  vpc_security_group_ids = module.vpc.default_vpc_default_security_group_id

  maintenance_window              = "Mon:00:00-Mon:03:00"
  backup_window                   = "03:00-06:00"
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  create_cloudwatch_log_group     = true

  backup_retention_period = 1
  skip_final_snapshot     = true
  deletion_protection     = false

  performance_insights_enabled          = true
  performance_insights_retention_period = 7
  create_monitoring_role                = true
  monitoring_interval                   = 60
  monitoring_role_name                  = "example-monitoring-role-name"
  monitoring_role_use_name_prefix       = true
  monitoring_role_description           = "Description for monitoring role"

  parameters = [
    {
      name  = "autovacuum"
      value = 1
    },
    {
      name  = "client_encoding"
      value = "utf8"
    }
  ]

}

resource "random_password" "rds_password" {
  length           = 16
  special          = true
  override_special = "!#$%&*-_=+[]{}<>:?"
}

resource "null_resource" "rds_setup_1" {
  # We expect psql to be installed to execute SQL commands at the end of terraform apply.
  provisioner "local-exec" {
    command = "psql --echo-queries -h \"${module.db.db_instance_endpoint}\" -U \"${module.db.db_instance_username}\" postgres1 -f ${path.module}/schema.sql -v base_name=\"${local.database_name}\""
    environment = {
      PGPASSWORD = nonsensitive(random_password.rds_password.result)
    }
  }
  triggers = {
    always_run = timestamp()
  }
}
