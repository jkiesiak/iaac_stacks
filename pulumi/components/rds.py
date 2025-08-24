import json

import pulumi
import pulumi_aws as aws
import pulumi_command as command
from naming_utils import get_resource_name
from pulumi_random import RandomPassword

from .tags import get_common_tags


class RdsStack(pulumi.ComponentResource):
    def __init__(
        self,
        name: str,
        env: str,
        vpc_id: pulumi.Input[str],
        subnet_ids: pulumi.Input[list],
        rds_security_group_id: pulumi.Input[str],
        is_development: bool = True,
        opts: pulumi.ResourceOptions = None,
    ):
        super().__init__("custom:RdsStack", name, None, opts)

        tags = get_common_tags(env)

        # Random password for PostgreSQL user
        rds_password = RandomPassword(
            resource_name=get_resource_name(f"rds-password-access", env),
            length=16,
            override_special="_%@",
            opts=pulumi.ResourceOptions(parent=self),
        )

        rds_secret = aws.secretsmanager.Secret(
            resource_name=get_resource_name(f"rds-secret-access", env),
            name=f"rds-secret-access-{env}",
            description="Credentials for PostgreSQL RDS",
            tags=tags,
            opts=pulumi.ResourceOptions(parent=self),
        )

        secret_version = aws.secretsmanager.SecretVersion(
            resource_name=get_resource_name(f"rds-secret-version", env),
            secret_id=rds_secret.id,
            secret_string=rds_password.result.apply(
                lambda pwd: json.dumps(
                    {
                        "username": "postgres",
                        "password": pwd,
                    }
                )
            ),
            opts=pulumi.ResourceOptions(parent=rds_secret),
        )
        # DB Subnet Group
        db_subnet_group = aws.rds.SubnetGroup(
            resource_name=get_resource_name("rds-subnet-group", env),
            subnet_ids=subnet_ids,
            description="RDS subnet group",
            tags={**tags, "Name": get_resource_name("rds-subnet-group", env)},
            opts=pulumi.ResourceOptions(parent=self),
        )

        # RDS Instance
        db_instance = aws.rds.Instance(
            resource_name=get_resource_name("rds-instance", env),
            identifier=f"rds-instance-{env}",
            instance_class="db.t3.micro",
            engine="postgres",
            engine_version="16.6",
            username="postgres",
            password=rds_password.result,
            allocated_storage=50,
            storage_type="gp2",
            db_subnet_group_name=db_subnet_group.name,
            vpc_security_group_ids=[rds_security_group_id],
            multi_az=not is_development,
            backup_retention_period=7,
            maintenance_window="wed:04:06-wed:04:36",
            auto_minor_version_upgrade=False,
            enabled_cloudwatch_logs_exports=["postgresql"],
            parameter_group_name="default.postgres16",
            publicly_accessible=True,
            skip_final_snapshot=is_development,
            deletion_protection=not is_development,
            copy_tags_to_snapshot=True,
            iam_database_authentication_enabled=True,
            storage_encrypted=True,
            tags={**tags, "Name": get_resource_name("rds-instance", env)},
            opts=pulumi.ResourceOptions(parent=self),
        )

        # Trigger logic: setup schema in database
        command.local.Command(
            "apply_db_schema",
            create=pulumi.Output.all(db_instance.address, rds_password.result).apply(
                lambda args: f"psql --echo-queries -h {args[0]} -U postgres -f sql_schema/schema.sql"
            ),
            environment=pulumi.Output.all(rds_password.result).apply(
                lambda args: {"PGPASSWORD": args[0]}
            ),
            opts=pulumi.ResourceOptions(
                depends_on=[db_instance]
            ),  # Ensures DB exists and is ready
        )

        self.rds_instance_arn = db_instance.arn
        self.rds_endpoint = db_instance.address
        self.rds_secret_name = rds_secret.name
        self.secret_arn = rds_secret.arn

        self.register_outputs(
            {
                "rds_instance_arn": self.rds_instance_arn,
                "rds_endpoint": self.rds_endpoint,
                "rds_secret_name": self.rds_secret_name,
                "secret_arn": self.secret_arn,
            }
        )
