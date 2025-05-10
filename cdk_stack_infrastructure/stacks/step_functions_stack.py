from aws_cdk import (
    Stack,
    Duration,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_s3 as s3,
    aws_logs as logs,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    aws_events as events,
    aws_events_targets as targets,
)
from constructs import Construct


class LambdaRdsStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        name_alias = "dev"

        # S3 Buckets
        s3_event_data = s3.Bucket(self, "S3EventDataBucket")
        s3_backup_data = s3.Bucket(self, "S3BackupDataBucket")

        # IAM Role for Lambda
        lambda_role = iam.Role(
            self, "LambdaExecutionRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com")
        )

        lambda_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
        )

        lambda_role.add_to_policy(iam.PolicyStatement(
            actions=["s3:GetObject", "s3:ListBucket"],
            resources=[s3_event_data.bucket_arn, f"{s3_event_data.bucket_arn}/*"]
        ))

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
            self, "InsertDataIntoRds",
            runtime=_lambda.Runtime.PYTHON_3_8,
            handler="lambda_handler.lambda_handler",
            code=_lambda.Code.from_asset("lambda_insert_data_into_rds"),
            role=lambda_role,
            timeout=Duration.seconds(300),
            function_name=f"lambda_insert_data_into_rds-{name_alias}",
            layers=[pg8000_layer, logging_layer],
            environment={
                "S3_BACKUP_DATA": s3_backup_data.bucket_name,
                "S3_EVENT_DATA": s3_event_data.bucket_name,
                "RDS_HOST": "<rds-host>" , # pass as param/env
                "SSM_NAME": "<secret-name>",
                "RDS_DB": "<db-name>"
            }
        )


        # Log Group
        log_group = logs.LogGroup(
            self, "LambdaStoreBackupLogGroup",
            log_group_name=f"/aws/lambda/lambda_store_backup-{name_alias}",
            retention=logs.RetentionDays.ONE_WEEK
        )

        # IAM Role
        lambda_store_backup_role = iam.Role(
            self, "LambdaStoreBackupRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com")
        )

        lambda_store_backup_policy = iam.Policy(
            self, "LambdaStoreBackupPolicy",
            statements=[
                iam.PolicyStatement(
                    actions=[
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents"
                    ],
                    resources=[
                        f"arn:aws:logs:{Stack.of(self).region}:{Stack.of(self).account}:log-group:/aws/lambda/lambda_store_backup-{name_alias}:*"
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
        lambda_store_backup_policy.attach_to_role(lambda_store_backup_role)

        # Lambda Function - lambda_store_backup
        lambda_store_backup = _lambda.Function(
            self, "LambdaStoreBackup",
            function_name=f"lambda_store_backup-{name_alias}",
            code=_lambda.Code.from_asset("lambda_store_backup"),
            role=lambda_role,

        handler="lambda_handler.lambda_handler",
            runtime=_lambda.Runtime.PYTHON_3_9,
            timeout=Duration.seconds(300),
            layers=[ logging_layer],

            environment={
                "S3_BACKUP_DATA": s3_backup_data.bucket_name,
                "S3_EVENT_DATA": s3_event_data.bucket_name
            },
        )

        lambda_store_backup.node.add_dependency(log_group)
        lambda_store_backup.node.add_dependency(lambda_store_backup_policy)

        # Step Function Definition
        insert_task = tasks.LambdaInvoke(
            self, "InsertIntoRDS",
            lambda_function=insert_lambda,
            output_path="$.Payload"
        )

        store_backup_task = tasks.LambdaInvoke(
            self, "StoreBackup",
            lambda_function=lambda_store_backup,
            output_path="$.Payload"
        )

        definition = insert_task.add_catch(
            sfn.Fail(self, "InsertFailure"),
            errors=["States.ALL"],
            result_path="$.error"
        ).next(store_backup_task.add_catch(
            sfn.Fail(self, "BackupFailure"),
            errors=["States.ALL"],
            result_path="$.error"
        ))

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
            state_machine_name=f"file-processing-flow-{name_alias}"
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
            assumed_by=iam.ServicePrincipal("events.amazonaws.com")
        )

        eventbridge_role.add_to_policy(iam.PolicyStatement(
            actions=["states:StartExecution"],
            resources=[state_machine.state_machine_arn]
        ))

        rule.add_target(targets.SfnStateMachine(state_machine, role=eventbridge_role))
