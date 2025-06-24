from aws_cdk import (
    Stack,
    Duration,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_s3 as s3,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    aws_events as events,
    aws_events_targets as targets,
    RemovalPolicy,
)
from constructs import Construct
from naming_utils import get_resource_name


class LambdaRdsStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        rds_instance_id: str,
        rds_endpoint_address: str,
        rds_secret_name: str,
        secret_arn: str,
        env: str = "dev",
        **kwargs,
    ):
        super().__init__(scope, id, **kwargs)

        self.env = env

        s3_event_data = s3.Bucket(
            self,
            f"S3EventDataBucket-{self.env}",
            bucket_name=get_resource_name("s3-event-data", self.env),
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            event_bridge_enabled=True,
        )

        s3_backup_data = s3.Bucket(
            self,
            f"S3BackupDataBucket-{self.env}",
            bucket_name=get_resource_name("s3-backup-data", self.env),
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        # IAM Role for Lambda
        lambda_role = iam.Role(
            self,
            f"LambdaInsertDataIntoRDS-{self.env}",
            role_name=get_resource_name("lambda-insert-data", self.env),
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
        )

        lambda_policy = iam.ManagedPolicy(
            self,
            f"LambdaEssentialPolicy-{self.env}",
            managed_policy_name=get_resource_name(
                "lambda_insert_data_into_rds_policy", self.env
            ),
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents",
                    ],
                    resources=[f"arn:aws:logs:{self.region}:{self.account}:*"],
                ),
                # S3 permissions
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["s3:GetObject", "s3:ListBucket"],
                    resources=[
                        s3_event_data.bucket_arn,
                        f"{s3_event_data.bucket_arn}/*",
                    ],
                ),
                # RDS permissions
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "rds-data:ExecuteStatement",
                        "rds-data:BatchExecuteStatement",
                        "rds-db:connect",
                    ],
                    resources=[rds_instance_id],
                ),
                # Secrets Manager permissions
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "secretsmanager:GetSecretValue",
                        "secretsmanager:DescribeSecret",
                    ],
                    resources=[secret_arn],
                ),
            ],
        )

        lambda_role.add_managed_policy(lambda_policy)

        # Define Lambda Layers
        pg8000_layer = _lambda.LayerVersion(
            self,
            f"Pg8000Layer-{self.env}",
            code=_lambda.Code.from_asset("dependencies/pg8000.zip"),
            compatible_runtimes=[
                _lambda.Runtime.PYTHON_3_8,
                _lambda.Runtime.PYTHON_3_9,
            ],
            layer_version_name="python_pg8000_layer",
        )

        logging_layer = _lambda.LayerVersion(
            self,
            f"LoggingLayer-{self.env}",
            code=_lambda.Code.from_asset("dependencies/logging_layer.zip"),
            compatible_runtimes=[
                _lambda.Runtime.PYTHON_3_8,
                _lambda.Runtime.PYTHON_3_9,
            ],
            layer_version_name="python_logging_layer",
        )

        # Lambda Function to insert into RDS
        lambda_insert_data_into_rds = _lambda.Function(
            self,
            f"InsertDataIntoRds-{self.env}",
            function_name=get_resource_name("lambda_insert_data_into_rds", self.env),
            runtime=_lambda.Runtime.PYTHON_3_8,
            handler="lambda_handler.lambda_handler",
            code=_lambda.Code.from_asset("lambda_insert_data_into_rds"),
            role=lambda_role,
            timeout=Duration.seconds(300),
            layers=[pg8000_layer, logging_layer],
            environment={
                "S3_BACKUP_DATA": s3_backup_data.bucket_name,
                "S3_EVENT_DATA": s3_event_data.bucket_name,
                "RDS_HOST": rds_endpoint_address,  # pass as param/env
                "SSM_NAME": rds_secret_name,
                "RDS_DB": "database_rds",
            },
        )

        # IAM Role
        lambda_store_backup_role = iam.Role(
            self,
            f"LambdaStoreBackupRole-{self.env}",
            role_name=get_resource_name("lambda-store-backup", self.env),
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
        )

        lambda_store_backup_policy = iam.ManagedPolicy(
            self,
            f"LambdaStoreBackupPolicy-{self.env}",
            managed_policy_name=get_resource_name(
                "lambda_store_backup-policy", self.env
            ),
            statements=[
                iam.PolicyStatement(
                    actions=[
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents",
                    ],
                    resources=[f"arn:aws:logs:{self.region}:{self.account}:*"],
                ),
                iam.PolicyStatement(
                    actions=["s3:GetObject", "s3:ListBucket", "s3:DeleteObject"],
                    resources=[
                        s3_event_data.bucket_arn,
                        f"{s3_event_data.bucket_arn}/*",
                    ],
                ),
                iam.PolicyStatement(
                    actions=["s3:PutObject", "s3:PutObjectAcl"],
                    resources=[f"{s3_backup_data.bucket_arn}/*"],
                ),
            ],
        )

        lambda_store_backup_role.add_managed_policy(lambda_store_backup_policy)

        lambda_store_backup = _lambda.Function(
            self,
            f"LambdaStoreBackup-{self.env}",
            function_name=get_resource_name("lambda_store_backup", self.env),
            code=_lambda.Code.from_asset("lambda_store_backup"),
            role=lambda_store_backup_role,
            handler="lambda_handler.lambda_handler",
            runtime=_lambda.Runtime.PYTHON_3_9,
            timeout=Duration.seconds(300),
            layers=[logging_layer],
            environment={
                "S3_BACKUP_DATA": s3_backup_data.bucket_name,
                "S3_EVENT_DATA": s3_event_data.bucket_name,
            },
        )

        # Step Function Definition
        insert_task = tasks.LambdaInvoke(
            self,
            f"InsertIntoRDS-{self.env}",
            lambda_function=lambda_insert_data_into_rds,
            output_path="$.Payload",
        ).add_retry(max_attempts=3, interval=Duration.seconds(2), backoff_rate=2.0)

        tasks_definition = (
            tasks.LambdaInvoke(
                self,
                f"StoreBackup-{self.env}",
                lambda_function=lambda_store_backup,
                output_path="$.Payload",
            )
            .add_retry(max_attempts=3, interval=Duration.seconds(2), backoff_rate=2.0)
            .add_catch(
                handler=sfn.Fail(
                    self,
                    "StoreBackupFail",
                    error="BackupFailed",
                    cause="Failed to backup file.",
                ),
                errors=["States.ALL"],
                result_path="$.error",
            )
        )

        definition = insert_task.next(tasks_definition)

        step_role = iam.Role(
            self,
            f"StepFunctionExecutionRole-{self.env}",
            role_name=get_resource_name("step-funct-execution-role", self.env),
            assumed_by=iam.ServicePrincipal("states.amazonaws.com"),
        )

        step_role.add_to_policy(
            iam.PolicyStatement(actions=["lambda:InvokeFunction"], resources=["*"])
        )

        state_machine = sfn.StateMachine(
            self,
            f"StepFunctions-{self.env}",
            state_machine_name=get_resource_name(
                "step-functions-processing-flow", self.env
            ),
            definition=definition,
            role=step_role,
        )

        # EventBridge Rule
        rule = events.Rule(
            self,
            f"S3PutObjectRule-{self.env}",
            event_pattern=events.EventPattern(
                source=["aws.s3"],
                detail_type=["Object Created"],
                detail={"bucket": {"name": [s3_event_data.bucket_name]}},
            ),
        )

        # Role to allow EventBridge to invoke Step Function
        eventbridge_role = iam.Role(
            self,
            f"EventBridgeInvokeRole-{self.env}",
            role_name=get_resource_name("invoke-stepfunctions-role", self.env),
            assumed_by=iam.ServicePrincipal("events.amazonaws.com"),
        )

        eventbridge_role.add_to_policy(
            iam.PolicyStatement(
                actions=["states:StartExecution"],
                resources=[state_machine.state_machine_arn],
            )
        )

        rule.add_target(targets.SfnStateMachine(state_machine, role=eventbridge_role))
