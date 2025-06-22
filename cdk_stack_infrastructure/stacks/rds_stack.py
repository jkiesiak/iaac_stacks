from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_secretsmanager as secretsmanager,
    RemovalPolicy,
    CfnOutput,
    Tags,
    aws_iam as iam,
    aws_lambda as _lambda,
    Duration,
    CustomResource
)
from constructs import Construct
from aws_cdk.custom_resources import Provider
import random
import string
import json
from datetime import datetime


class RdsPostgresStack(Stack):
    def __init__(self, scope: Construct, id: str, vpc: ec2.IVpc, rds_security_group: ec2.ISecurityGroup, env: str = "dev", **kwargs):
        super().__init__(scope, id, **kwargs)

        is_development = True

        # Create naming convention helper
        def get_resource_name(resource_type: str) -> str:
            """Generate consistent resource names with env prefix"""
            return f"{resource_type}-{env}"

        # # Generate random password for RDS
        # password_length = 16
        # password_chars = string.ascii_letters + string.digits + "!#$%&*-_=+[]{}<>:?"
        # random_password = ''.join(random.choice(password_chars) for _ in range(password_length))

        # Create a secret in Secrets Manager to store the password
        rds_password_secret = secretsmanager.Secret(
            self,
            f"RdsPasswordSecret{name_alias}",
            secret_name=get_resource_name("rds-password"),
            description=f"RDS password for user {name_alias}",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template=json.dumps({"username": "postgres"}),
                generate_string_key="password",
                exclude_characters="\"@/\\",
                password_length=16,
                exclude_punctuation=False,
                include_space=False,
                require_each_included_type=True
            )
        )

        # Create RDS PostgreSQL instance
        postgres_rds = rds.DatabaseInstance(
            self,
            "PostgresRdsInstance",
            instance_identifier=get_resource_name("rds-database"),
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_16_6
            ),
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.T3,
                ec2.InstanceSize.MICRO
            ),
            credentials=rds.Credentials.from_secret(rds_password_secret, username="postgres"),
            allocated_storage=50,
            storage_type=rds.StorageType.GP2,
            storage_encrypted=True,
            vpc=vpc,
            security_groups=[rds_security_group],
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PUBLIC
            ),
            removal_policy=RemovalPolicy.SNAPSHOT if not is_development else RemovalPolicy.DESTROY,
            deletion_protection=not is_development,
            publicly_accessible=True,
            multi_az=True,
            copy_tags_to_snapshot=True,
            enable_performance_insights=True,
            # performance_insight_retention=rds.PerformanceInsightRetention.DEFAULT, default is 7 days in docs
            backup_retention=Duration.days(7),
            preferred_maintenance_window="Wed:04:06-Wed:04:36",
            auto_minor_version_upgrade=False,
            cloudwatch_logs_exports=["postgresql"],
            iam_authentication=True,
            parameter_group=rds.ParameterGroup.from_parameter_group_name(
                self,
                "ParameterGroup",
                parameter_group_name="default.postgres16"
            )
        )
        self.rds_endpoint_address = postgres_rds.db_instance_endpoint_address
        self.rds_password_secret = rds_password_secret.secret_name
        self.rds_instance_id = postgres_rds.instance_arn
        self.secret_arn = rds_password_secret.secret_arn

        # Apply database schema using a custom resource
        # no psql for cdk v2
        schema_setup_role = iam.Role(
            self,
            "SchemaSetupRole",
            role_name=get_resource_name("schema-setup"),
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies = [iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")]
        )

        schema_setup_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "secretsmanager:GetSecretValue",
                    "secretsmanager:DescribeSecret"
                ],
                resources=[rds_password_secret.secret_arn]
            )
        )

        # Lambda to execute PostgreSQL schema setup
        schema_setup_lambda = _lambda.Function(
            self,
            f"SchemaSetupLambda",
            function_name=get_resource_name("lambda-setup-schema"),
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="index.handler",
            code=_lambda.Code.from_asset("apply_sql_schema"),
            timeout=Duration.minutes(5),
            role=schema_setup_role,
            environment={
                "SECRET_NAME": rds_password_secret.secret_name,
                "DB_HOST": postgres_rds.db_instance_endpoint_address,
            },
            layers=[
                _lambda.LayerVersion(
                    self,
                    "PsycopgLayer",
                    code=_lambda.Code.from_asset("dependencies/pg8000.zip"),
                    compatible_runtimes=[_lambda.Runtime.PYTHON_3_9],
                )
            ]
        )

        # Custom resource to trigger schema setup for RDS database
        schema_setup_provider = Provider(
            self,
            "SchemaSetupProvider",
            on_event_handler=schema_setup_lambda
        )

        # Custom resource to trigger the Lambda
        schema_custom_resource = CustomResource(
            self, "RunSchemaOnDeploy",
            service_token=schema_setup_provider.service_token,
            # Include properties that should trigger a re-execution
            # Adding a timestamp ensures it runs on every deployment
            properties={
                "timestamp": datetime.now().isoformat(),
                "dbIdentifier": postgres_rds.instance_identifier,
            }
        )

        # # Add dependency to ensure RDS is created before schema setup
        schema_setup_lambda.node.add_dependency(postgres_rds)
        schema_custom_resource.node.add_dependency(postgres_rds)

