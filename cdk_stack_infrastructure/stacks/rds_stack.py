from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_secretsmanager as secretsmanager,
    RemovalPolicy,
    CfnOutput,
    Tags,
    custom_resources as cr,
    aws_iam as iam,
    aws_lambda as lambda_,
    Duration,
)
from constructs import Construct
import random
import string
import json


class RdsPostgresStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, vpc,
                 name_alias: str,
                 rds_security_group,
                 # db_subnet_group: rds.CfnDBSubnetGroup,
                 **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        is_development = True
        # Generate random password for RDS
        password_length = 16
        password_chars = string.ascii_letters + string.digits + "!#$%&*-_=+[]{}<>:?"
        random_password = ''.join(random.choice(password_chars) for _ in range(password_length))

        # Create a secret in Secrets Manager to store the password
        rds_password_secret = secretsmanager.Secret(
            self,
            f"RdsPasswordSecret{name_alias}",
            # secret_name=f"rds-password-{name_alias}",
            description=f"RDS password for user {name_alias}",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template=json.dumps({"username": "postgres"}),
                generate_string_key="password",
                exclude_characters="\"@/\\",
                password_length=password_length,
                exclude_punctuation=False,
                include_space=False,
                require_each_included_type=True
            )
        )

        Tags.of(rds_password_secret).add("Environment", "production")

        # Create RDS PostgreSQL instance
        postgres_rds = rds.DatabaseInstance(
            self,
            "PostgresRdsInstance",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_16_6
            ),
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.T3,
                ec2.InstanceSize.MICRO
            ),
            credentials=rds.Credentials.from_secret(rds_password_secret, username="postgres"),
            instance_identifier=f"rds-database-{name_alias}",
            allocated_storage=50,
            storage_type=rds.StorageType.GP2,
            storage_encrypted=True,
            vpc=vpc,
            security_groups=[rds_security_group],
            # vpc_subnets=ec2.SubnetSelection(
            #     subnet_group_name=db_subnet_group.db_subnet_group_name
            # ),
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
        # schema_setup_role = iam.Role(
        #     self,
        #     "SchemaSetupRole",
        #     assumed_by=iam.ServicePrincipal("lambda.amazonaws.com")
        # )
        #
        # schema_setup_role.add_managed_policy(
        #     iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
        # )
        #
        # schema_setup_role.add_to_policy(
        #     iam.PolicyStatement(
        #         effect=iam.Effect.ALLOW,
        #         actions=[
        #             "secretsmanager:GetSecretValue"
        #         ],
        #         resources=[rds_password_secret.secret_arn]
        #     )
        # )
        #
        # # Lambda to execute PostgreSQL schema setup
        # schema_setup_lambda = lambda_.Function(
        #     self,
        #     "SchemaSetupLambda",
        #     runtime=lambda_.Runtime.PYTHON_3_9,
        #     handler="index.handler",
        #     code=lambda_.Code.from_inline("""
        # raise e
        #     """),
        #     timeout=Duration.minutes(5),
        #     role=schema_setup_role,
        #     environment={
        #         "SECRET_NAME": rds_password_secret.secret_name,
        #         "DB_HOST": postgres_rds.db_instance_endpoint_address,
        #     },
        #     layers=[
        #         lambda_.LayerVersion(
        #             self,
        #             "PsycopgLayer",
        #             code=lambda_.Code.from_asset("lambda_layers/psycopg2.zip"),
        #             compatible_runtimes=[lambda_.Runtime.PYTHON_3_9],
        #         )
        #     ]
        # )
        #
        # # Custom resource to trigger schema setup
        # schema_setup_provider = cr.Provider(
        #     self,
        #     "SchemaSetupProvider",
        #     on_event_handler=schema_setup_lambda
        # )
        #
        # schema_setup = cr.CustomResource(
        #     self,
        #     "SchemaSetup",
        #     service_token=schema_setup_provider.service_token,
        #     properties={
        #         "Timestamp": self.node.try_get_context("deployment_timestamp") or "initial",
        #     },
        #     removal_policy=RemovalPolicy.RETAIN
        # )
        #
        # # Add dependency to ensure RDS is created before schema setup
        # schema_setup.node.add_dependency(postgres_rds)
        #
        # # Outputs
        # CfnOutput(
        #     self,
        #     "RdsEndpoint",
        #     value=postgres_rds.db_instance_endpoint_address,
        #     description="The endpoint of the RDS PostgreSQL instance"
        # )
        #
        # CfnOutput(
        #     self,
        #     "RdsSecretName",
        #     value=rds_password_secret.secret_name,
        #     description="Name of the secret containing the RDS credentials"
        # )