from aws_cdk import (
    Stack,
    Duration,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_s3 as s3,
    aws_s3_notifications as s3n,

    aws_logs as logs,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    aws_events as events,
    aws_events_targets as targets,
RemovalPolicy
)
from constructs import Construct


class LambdaRdsStack(Stack):
    def __init__(self, scope: Construct, construct_id: str,rds_instance_id,  name_alias: str,
                 rds_endpoint_address, rds_secret_name, secret_arn,  **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        env = self.node.try_get_context("env")

        is_development = env == "prod"

        s3_event_data = s3.Bucket(self, f"S3EventDataBucket-{name_alias}",
                                  # bucket_name=f"s3-event-data-{name_alias}",
                                  removal_policy=RemovalPolicy.DESTROY,
                                  auto_delete_objects=True,
                                  event_bridge_enabled=True
                                  )


        s3_backup_data = s3.Bucket(self, f"S3BackupDataBucket-{name_alias}",
                                   # bucket_name=f"bucket-backup-data-{name_alias}",
                                   removal_policy=RemovalPolicy.DESTROY,
                                   auto_delete_objects=True
                                   )

        # IAM Role for Lambda
        lambda_role = iam.Role(
            self, f"LambdaInsertDataIntoRDS-{name_alias}",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com")
        )

        lambda_policy = iam.ManagedPolicy(
            self, "LambdaEssentialPolicy",
            managed_policy_name=f"lambda_insert_data_into_rds-policy-{name_alias}",
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents"
                    ],
                    resources=[
                        f"arn:aws:logs:{self.region}:{self.account}:*"
                    ]
                ),
                # S3 permissions
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "s3:GetObject",
                        "s3:ListBucket"
                    ],
                    resources=[
                        s3_event_data.bucket_arn,
                        f"{s3_event_data.bucket_arn}/*"
                    ]
                ),
                # RDS permissions
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "rds-data:ExecuteStatement",
                        "rds-data:BatchExecuteStatement",
                        "rds-db:connect"
                    ],
                    resources=[
                        rds_instance_id
                    ]
                ),
                # Secrets Manager permissions
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "secretsmanager:GetSecretValue",
                        "secretsmanager:DescribeSecret"
                    ],
                    resources=[
                        secret_arn
                    ]
                )
            ]
        )

        lambda_role.add_managed_policy(lambda_policy)


        # Define Lambda Layers
        pg8000_layer = _lambda.LayerVersion(
            self, "Pg8000Layer",
            code=_lambda.Code.from_asset("dependencies/pg8000.zip"),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_8, _lambda.Runtime.PYTHON_3_9],
            layer_version_name="python_pg8000_layer"
        )

        logging_layer = _lambda.LayerVersion(
            self, "LoggingLayer",
            code=_lambda.Code.from_asset("dependencies/logging_layer.zip"),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_8, _lambda.Runtime.PYTHON_3_9],
            layer_version_name="python_logging_layer"
        )

        # Lambda Function to insert into RDS
        lambda_insert_data_into_rds = _lambda.Function(
            self, f"InsertDataIntoRds-{name_alias}",
            runtime=_lambda.Runtime.PYTHON_3_8,
            handler="lambda_handler.lambda_handler",
            code=_lambda.Code.from_asset("lambda_insert_data_into_rds"),
            role=lambda_role,
            timeout=Duration.seconds(300),
            # function_name=f"lambda_insert_data_into_rds-{name_alias}",
            layers=[pg8000_layer, logging_layer],
            environment={
                "S3_BACKUP_DATA": s3_backup_data.bucket_name,
                "S3_EVENT_DATA": s3_event_data.bucket_name,
                "RDS_HOST": rds_endpoint_address , # pass as param/env
                "SSM_NAME": rds_secret_name,
                "RDS_DB": "database_rds"
            }
        )


        # # Log Group
        # log_group = logs.LogGroup(
        #     self, f"LambdaStoreBackupLogGroup{name_alias}",
        #     # log_group_name=f"/aws/lambda/lambda_store_backup-{name_alias}",
        #     retention=logs.RetentionDays.ONE_WEEK
        # )

        # IAM Role
        lambda_store_backup_role = iam.Role(
            self, f"LambdaStoreBackupRole-{name_alias}",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com")
        )

        lambda_store_backup_policy = iam.ManagedPolicy(
            self, f"LambdaStoreBackupPolicy-{name_alias}",
            # managed_policy_name=f"lambda_store_backup-policy-{name_alias}",
            statements=[
                iam.PolicyStatement(
                    actions=[
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents"
                    ],
                    resources=[
                        f"arn:aws:logs:{self.region}:{self.account}:*"
                    ]
                ),
                iam.PolicyStatement(
                    actions=["s3:GetObject", "s3:ListBucket", "s3:DeleteObject"],
                    resources=[
                        s3_event_data.bucket_arn,
                        f"{s3_event_data.bucket_arn}/*"
                    ]
                ),
                iam.PolicyStatement(
                    actions=["s3:PutObject", "s3:PutObjectAcl"],
                    resources=[f"{s3_backup_data.bucket_arn}/*"]
                )
            ]
        )

        lambda_store_backup_role.add_managed_policy(lambda_store_backup_policy)

        # Lambda Function - lambda_store_backup
        lambda_store_backup = _lambda.Function(
            self, f"LambdaStoreBackup-{name_alias}",
            # function_name=f"lambda_store_backup-{name_alias}",
            code=_lambda.Code.from_asset("lambda_store_backup"),
            role=lambda_store_backup_role,
            handler="lambda_handler.lambda_handler",
            runtime=_lambda.Runtime.PYTHON_3_9,
            timeout=Duration.seconds(300),
            layers=[ logging_layer],

            environment={
                "S3_BACKUP_DATA": s3_backup_data.bucket_name,
                "S3_EVENT_DATA": s3_event_data.bucket_name
            },
        )


        # Step Function Definition
        insert_task = tasks.LambdaInvoke(
            self, "InsertIntoRDS",
            lambda_function=lambda_insert_data_into_rds,
            output_path="$.Payload"
        ).add_retry(
            max_attempts=3,
            interval=Duration.seconds(2),
            backoff_rate=2.0
        )

        tasks_definition = tasks.LambdaInvoke(
            self, "StoreBackup",
            lambda_function=lambda_store_backup,
            output_path="$.Payload"
        ).add_retry(
            max_attempts=3,
            interval=Duration.seconds(2),
            backoff_rate=2.0
        ).add_catch(
            handler=sfn.Fail(
                self, "StoreBackupFail",
                error="BackupFailed",
                cause="Failed to backup file."
            ),
            errors=["States.ALL"],
            result_path="$.error"
        )

        definition = insert_task.next(tasks_definition)


        step_role = iam.Role(
            self, "StepFunctionExecutionRole",
            assumed_by=iam.ServicePrincipal("states.amazonaws.com")
        )

        step_role.add_to_policy(iam.PolicyStatement(
            actions=["lambda:InvokeFunction"],
            resources=["*"]
        ))

        state_machine = sfn.StateMachine(
            self, "StepFunction",
            definition=definition,
            role=step_role,
            # state_machine_name=f"file-processing-flow-{name_alias}"
        )

        # EventBridge Rule
        rule = events.Rule(
            self, "S3PutObjectRule",
            event_pattern=events.EventPattern(
                source=["aws.s3"],
                detail_type=["Object Created"],
                detail={"bucket": {"name": [s3_event_data.bucket_name]}}
            )
        )

        # Role to allow EventBridge to invoke Step Function
        eventbridge_role = iam.Role(
            self, "EventBridgeInvokeRole",
            role_name=f"eventbridge-invoke-stepfunction-role-{name_alias}",
            assumed_by=iam.ServicePrincipal("events.amazonaws.com")
        )

        eventbridge_role.add_to_policy(iam.PolicyStatement(
            actions=["states:StartExecution"],
            resources=[state_machine.state_machine_arn]
        ))

        rule.add_target(targets.SfnStateMachine(state_machine, role=eventbridge_role))
