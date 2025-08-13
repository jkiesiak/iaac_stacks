import pulumi
import pulumi_aws as aws
import json
from pulumi import ResourceOptions
from typing import Optional
from naming_utils import get_resource_name
from .tags import get_common_tags


class StepFunctionsStack(pulumi.ComponentResource):
    def __init__(
        self,
        name: str,
        env: str,
        rds_instance_arn: str,
        rds_endpoint_address: str,
        rds_secret_name: str,
        rds_secret_arn: str,
        opts: Optional[ResourceOptions] = None,
    ):
        super().__init__("custom:StepFunctionsStack", name, None, opts)
        tags = get_common_tags(env)

        account_id = aws.get_caller_identity().account_id
        region = aws.config.region

        # ------------------------------
        # S3 Buckets
        # ------------------------------
        s3_event_data = aws.s3.Bucket(
            get_resource_name("s3-event-data", env),
            bucket=get_resource_name("s3-event-data", env),
            force_destroy=True,
            tags=tags,
            opts=ResourceOptions(parent=self),
        )

        s3_backup_data = aws.s3.Bucket(
            get_resource_name("s3-backup-data", env),
            bucket=get_resource_name("s3-backup-data", env),
            force_destroy=True,
            tags=tags,
            opts=ResourceOptions(parent=self),
        )

        # Enable EventBridge notifications for buckets
        aws.s3.BucketNotification(
            get_resource_name("s3-event-data-eventbridge", env),
            bucket=s3_event_data.id,
            eventbridge=True,
            opts=ResourceOptions(parent=s3_event_data),
        )

        aws.s3.BucketNotification(
            get_resource_name("s3-backup-data-eventbridge", env),
            bucket=s3_backup_data.id,
            eventbridge=True,
            opts=ResourceOptions(parent=s3_backup_data),
        )

        # ------------------------------
        # Lambda Role for Insert Data
        # ------------------------------
        lambda_role = aws.iam.Role(
            get_resource_name("lambda-insert-role", env),
            assume_role_policy=json.dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Action": "sts:AssumeRole",
                            "Principal": {"Service": "lambda.amazonaws.com"},
                            "Effect": "Allow",
                        }
                    ],
                }
            ),
            opts=ResourceOptions(parent=self),
        )

        aws.iam.RolePolicy(
            get_resource_name("lambda-insert-policy", env),
            role=lambda_role.id,
            policy=pulumi.Output.all(
                s3_event_data.bucket, rds_instance_arn, rds_secret_arn
            ).apply(
                lambda arn: json.dumps(
                    {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Action": [
                                    "logs:CreateLogGroup",
                                    "logs:CreateLogStream",
                                    "logs:PutLogEvents",
                                ],
                                "Resource": "*",
                                "Effect": "Allow",
                            },
                            {
                                "Action": ["s3:GetObject", "s3:ListBucket"],
                                "Resource": [
                                    f"arn:aws:s3:::{arn[0]}",
                                    f"arn:aws:s3:::{arn[0]}/*",
                                ],
                                "Effect": "Allow",
                            },
                            {
                                "Action": [
                                    "rds-data:ExecuteStatement",
                                    "rds-data:BatchExecuteStatement",
                                    "rds-db:connect",
                                ],
                                "Resource": f"{arn[1]}",
                                "Effect": "Allow",
                            },
                            {
                                "Action": [
                                    "secretsmanager:GetSecretValue",
                                    "secretsmanager:DescribeSecret",
                                ],
                                "Resource": f"{arn[2]}",
                                "Effect": "Allow",
                            },
                        ],
                    }
                )
            ),
            opts=ResourceOptions(parent=lambda_role),
        )

        # ------------------------------
        # Lambda Layers (pre-uploaded zip files)
        # ------------------------------
        self.pg8000_layer = aws.lambda_.LayerVersion(
            get_resource_name("pg8000-layer", env),
            layer_name="python_pg8000_layer",
            compatible_runtimes=["python3.9"],
            code=pulumi.FileArchive("../pulumi/dependencies/pg8000.zip"),
            opts=ResourceOptions(parent=self),
        )

        self.logging_layer = aws.lambda_.LayerVersion(
            get_resource_name("logging-layer", env),
            layer_name="python_logging_layer",
            compatible_runtimes=["python3.9"],
            code=pulumi.FileArchive("../pulumi/dependencies/logging_layer.zip"),
            opts=ResourceOptions(parent=self),
        )

        # ------------------------------
        # Lambda Function to Insert into RDS
        # ------------------------------
        lambda_insert = aws.lambda_.Function(
            resource_name=get_resource_name("lambda_insert_data_into_rds", env),
            name=f"lambda_insert_data_into_rds-{env}",
            runtime="python3.9",
            handler="lambda_handler.lambda_handler",
            role=lambda_role.arn,
            timeout=300,
            memory_size=256,
            layers=[self.pg8000_layer.arn, self.logging_layer.arn],
            code=pulumi.AssetArchive(
                {".": pulumi.FileArchive("./lambda_insert_data_into_rds")}
            ),
            environment={
                "variables": {
                    "S3_BACKUP_DATA": s3_backup_data.bucket,
                    "S3_EVENT_DATA": s3_event_data.bucket,
                    "RDS_HOST": rds_endpoint_address,
                    "SSM_NAME": rds_secret_name,
                    "RDS_DB": "database_rds",
                }
            },
            opts=ResourceOptions(parent=self),
            tags={
                **tags,
                "Name": get_resource_name("lambda_insert_data_into_rds", env),
            },
        )

        # ------------------------------
        # Lambda for Backup
        # ------------------------------
        lambda_backup_role = aws.iam.Role(
            get_resource_name("lambda-backup-role", env),
            assume_role_policy=json.dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Action": "sts:AssumeRole",
                            "Principal": {"Service": "lambda.amazonaws.com"},
                            "Effect": "Allow",
                        }
                    ],
                }
            ),
            opts=ResourceOptions(parent=self),
        )

        aws.iam.RolePolicy(
            get_resource_name("lambda-backup-policy", env),
            role=lambda_backup_role.id,
            policy=pulumi.Output.all(s3_event_data.arn, s3_backup_data.arn).apply(
                lambda arn: json.dumps(
                    {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Action": [
                                    "logs:CreateLogGroup",
                                    "logs:CreateLogStream",
                                    "logs:PutLogEvents",
                                ],
                                "Resource": "*",
                                "Effect": "Allow",
                            },
                            {
                                "Action": [
                                    "s3:GetObject",
                                    "s3:ListBucket",
                                    "s3:DeleteObject",
                                ],
                                "Resource": [f"{arn[0]}", f"{arn[0]}/*"],
                                "Effect": "Allow",
                            },
                            {
                                "Action": ["s3:PutObject", "s3:PutObjectAcl"],
                                "Resource": f"{arn[1]}/*",
                                "Effect": "Allow",
                            },
                        ],
                    }
                )
            ),
            opts=ResourceOptions(parent=lambda_backup_role),
        )

        lambda_backup = aws.lambda_.Function(
            resource_name=get_resource_name("lambda_store_backup", env),
            name=f"lambda_store_backup-{env}",
            runtime="python3.9",
            handler="lambda_handler.lambda_handler",
            role=lambda_backup_role.arn,
            timeout=300,
            memory_size=256,
            layers=[self.logging_layer.arn],
            code=pulumi.AssetArchive(
                {".": pulumi.FileArchive("./lambda_store_backup")}
            ),
            environment={
                "variables": {
                    "S3_BACKUP_DATA": s3_backup_data.bucket,
                    "S3_EVENT_DATA": s3_event_data.bucket,
                }
            },
            opts=ResourceOptions(parent=self),
            tags={**tags, "Name": get_resource_name("lambda_store_backup", env)},
        )

        # ------------------------------
        # Step Function & Role
        # ------------------------------
        step_role = aws.iam.Role(
            get_resource_name("step-fn-role", env),
            assume_role_policy=json.dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Action": "sts:AssumeRole",
                            "Principal": {"Service": "states.amazonaws.com"},
                            "Effect": "Allow",
                        }
                    ],
                }
            ),
            opts=ResourceOptions(parent=self),
        )

        policy_definition = pulumi.Output.all(
            lambda_insert.arn, lambda_backup.arn
        ).apply(
            lambda arns: json.dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Action": "lambda:InvokeFunction",
                            "Resource": "*",
                            "Effect": "Allow",
                        },
                        {
                            "Action": "lambda:InvokeFunction",
                            "Resource": [arns[0], f"{arns[0]}:*"],
                            "Effect": "Allow",
                        },
                        {
                            "Action": "lambda:InvokeFunction",
                            "Resource": [
                                arns[1],
                                f"{arns[1]}:*",
                            ],
                            "Effect": "Allow",
                        },
                    ],
                }
            )
        )

        aws.iam.RolePolicy(
            get_resource_name("step-fn-invoke-policy", env),
            role=step_role.name,
            policy=policy_definition,
            opts=ResourceOptions(parent=step_role),
        )

        step_definition = pulumi.Output.all(lambda_insert.arn, lambda_backup.arn).apply(
            lambda arns: json.dumps(
                {
                    "Comment": "State machine definition",
                    "StartAt": "InsertIntoRDS",
                    "States": {
                        "InsertIntoRDS": {
                            "Type": "Task",
                            "Resource": arns[0],
                            "Next": "StoreBackup",
                        },
                        "StoreBackup": {
                            "Type": "Task",
                            "Resource": arns[1],
                            "Retry": [
                                {
                                    "ErrorEquals": ["States.ALL"],
                                    "IntervalSeconds": 2,
                                    "MaxAttempts": 3,
                                    "BackoffRate": 2.0,
                                }
                            ],
                            "Catch": [
                                {
                                    "ErrorEquals": ["States.ALL"],
                                    "Next": "BackupFail",
                                    "ResultPath": "$.error",
                                }
                            ],
                            "End": True,
                        },
                        "BackupFail": {
                            "Type": "Fail",
                            "Error": "BackupFailed",
                            "Cause": "Failed to backup file.",
                        },
                    },
                }
            )
        )

        state_machine = aws.sfn.StateMachine(
            get_resource_name("step-fn", env),
            role_arn=step_role.arn,
            definition=step_definition,
            name=get_resource_name("step-functions-processing-flow", env),
            opts=ResourceOptions(parent=self),
            tags={**tags, "Name": get_resource_name("step-fn", env)},
        )

        # ------------------------------
        # EventBridge Rule
        # ------------------------------
        eventbridge_role = aws.iam.Role(
            get_resource_name("eventbridge-role", env),
            assume_role_policy=json.dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Action": "sts:AssumeRole",
                            "Principal": {"Service": "events.amazonaws.com"},
                            "Effect": "Allow",
                        }
                    ],
                }
            ),
            opts=ResourceOptions(parent=self),
        )
        policy = state_machine.arn.apply(
            lambda arn: json.dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Action": ["states:StartExecution"],
                            "Resource": arn,
                        }
                    ],
                }
            )
        )

        aws.iam.RolePolicy(
            get_resource_name("eventbridge-policy", env),
            role=eventbridge_role.id,
            policy=policy,
            opts=ResourceOptions(parent=eventbridge_role),
        )

        event_pattern = s3_event_data.bucket.apply(
            lambda bucket_name: json.dumps(
                {
                    "source": ["aws.s3"],
                    "detail-type": ["Object Created"],
                    "detail": {"bucket": {"name": [bucket_name]}},
                }
            )
        )

        event_rule = aws.cloudwatch.EventRule(
            resource_name=get_resource_name("s3-put-event-rule", env),
            name=get_resource_name("s3-put-event-rule", env),
            event_pattern=event_pattern,
            opts=ResourceOptions(parent=self),
        )

        aws.cloudwatch.EventTarget(
            get_resource_name("stepfn-target", env),
            rule=event_rule.name,
            arn=state_machine.arn,
            role_arn=eventbridge_role.arn,
            opts=ResourceOptions(parent=event_rule),
        )

        self.register_outputs(
            {
                "s3_event_data_bucket": s3_event_data.id,
                "s3_backup_data_bucket": s3_backup_data.id,
                "step_function_arn": state_machine.arn,
                "pg8000_layer_arn": self.pg8000_layer.arn,
                "logging_layer_arn": self.logging_layer.arn,
            }
        )
