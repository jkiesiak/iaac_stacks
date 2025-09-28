resource "aws_sfn_state_machine" "preprocess_and_api_call" {
  name     = "file-processing-flow-${local.name_alias}"
  role_arn = aws_iam_role.stepfunction_role.arn

  definition = jsonencode({
    Comment = "Process file from S3 and back it up after successful database insert",
    StartAt = "InsertIntoRDS",
    States = {
      InsertIntoRDS = {
        Type     = "Task",
        Resource = aws_lambda_function.lambda_data_preprocessing.arn, # Lambda that INSERTS INTO RDS
        Next     = "StoreBackup"
        Retry = [
          {
            ErrorEquals     = ["States.ALL"],
            IntervalSeconds = 2,
            MaxAttempts     = 3,
            BackoffRate     = 2.0
          }
        ],
        Catch = [
          {
            ErrorEquals = ["States.ALL"],
            ResultPath  = "$.error",
            Next        = "Failure"
          }
        ]
      },
      StoreBackup = {
        Type     = "Task",
        Resource = aws_lambda_function.lambda_store_backup.arn, # Lambda that BACKUPS the file to another S3
        End      = true,
        Retry = [
          {
            ErrorEquals     = ["States.ALL"],
            IntervalSeconds = 2,
            MaxAttempts     = 3,
            BackoffRate     = 2.0
          }
        ],
        Catch = [
          {
            ErrorEquals = ["States.ALL"],
            ResultPath  = "$.error",
            Next        = "Failure"
          }
        ]
      },
      Failure = {
        Type  = "Fail",
        Error = "StepFunctionFailed",
        Cause = "Something went wrong during RDS insert or S3 backup."
      }
    }
  })
}


resource "aws_s3_bucket_notification" "s3_event_data_eventbridge" {
  bucket      = aws_s3_bucket.s3_event_data.id
  eventbridge = true

}

resource "aws_cloudwatch_event_rule" "s3_put_object" {
  name        = "trigger-step-function-from-s3-${local.name_alias}"
  description = "Trigger Step Function when object created in S3 bucket"

  event_pattern = jsonencode({
    source = ["aws.s3"],
    "detail-type" : ["Object Created"],
    detail = {
      bucket = {
        name = [aws_s3_bucket.s3_event_data.bucket]
      }
    }
  })
}

resource "aws_iam_role" "eventbridge_invoke_stepfunction_role" {
  name = "eventbridge-invoke-stepfunction-role-${local.name_alias}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          Service = "events.amazonaws.com"
        },
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "eventbridge_invoke_stepfunction_policy" {
  name = "eventbridge-invoke-stepfunction-policy-${local.name_alias}"

  role = aws_iam_role.eventbridge_invoke_stepfunction_role.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = "states:StartExecution",
        Resource = aws_sfn_state_machine.preprocess_and_api_call.arn
      }
    ]
  })
}


resource "aws_cloudwatch_event_target" "start_step_function" {
  rule      = aws_cloudwatch_event_rule.s3_put_object.name
  target_id = "StartStepFunction"
  arn       = aws_sfn_state_machine.preprocess_and_api_call.arn
  role_arn  = aws_iam_role.eventbridge_invoke_stepfunction_role.arn

  depends_on = [aws_sfn_state_machine.preprocess_and_api_call]

}


resource "aws_iam_role" "stepfunction_role" {
  name = "stepfunction-execution-role-${local.name_alias}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          Service = "states.amazonaws.com"
        },
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "stepfunction_policy" {
  name = "stepfunction-execution-policy-${local.name_alias}"

  role = aws_iam_role.stepfunction_role.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "lambda:InvokeFunction"
        ],
        Resource = "*"
      }
    ]
  })
}

resource "aws_s3_bucket" "s3_event_data" {
  bucket        = "bucket-event-data-${local.name_alias}"
  force_destroy = var.is_development
}

resource "aws_s3_bucket" "s3_backup_data" {
  bucket        = "bucket-backup-data-${local.name_alias}"
  force_destroy = var.is_development
}

resource "aws_lambda_function" "lambda_data_preprocessing" {
  function_name = "lambda_insert_data_into_rds-${local.name_alias}"

  filename         = "${path.module}/lambda/.output/lambda_handler.zip"
  layers           = [aws_lambda_layer_version.python_pg8000_layer.arn, aws_lambda_layer_version.python_logging_layer.arn]
  source_code_hash = data.archive_file.zip_the_python_code.output_base64sha256

  role    = aws_iam_role.lambda_role.arn
  handler = "lambda_handler.lambda_handler"
  runtime = "python3.8"
  timeout = 300

  environment {
    variables = {
      S3_BACKUP_DATA = aws_s3_bucket.s3_backup_data.bucket
      S3_EVENT_DATA  = aws_s3_bucket.s3_event_data.bucket
      RDS_HOST       = aws_db_instance.rds.address
      SSM_NAME       = aws_secretsmanager_secret.rds_password_secret.name
      RDS_DB         = var.rds_database_name
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.attach_essential_policies_to_lambda_role
  ]
}

data "archive_file" "zip_the_python_code" {
  type        = "zip"
  source_dir  = "${path.module}/lambda/src"
  output_path = "${path.module}/lambda/.output/lambda_handler.zip"
}

resource "aws_lambda_layer_version" "python_pg8000_layer" {
  filename   = "${path.module}/lambda/dependencies/pg8000.zip"
  layer_name = "python_pg8000_layer"

  compatible_runtimes = ["python3.8", "python3.9"]
}

resource "aws_lambda_layer_version" "python_logging_layer" {
  filename   = "${path.module}/lambda/dependencies/logging_layer.zip"
  layer_name = "python_logging_layer"

  compatible_runtimes = ["python3.8", "python3.9"]
}

resource "aws_iam_role" "lambda_role" {
  name = "lambda_insert_data_into_rds-role-${local.name_alias}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Principal = {
          Service = "lambda.amazonaws.com"
        },
        Effect = "Allow"
      }
    ]
  })
}

resource "aws_iam_policy" "lambda_essential_policies" {
  name = "lambda_insert_data_into_rds-policy-${local.name_alias}"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Resource = [
          "arn:aws:logs:${var.region_aws}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/lambda_insert_data_into_rds-${local.name_alias}:*"
        ]
      },
      {
        Effect = "Allow",
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ],
        Resource = [
          aws_s3_bucket.s3_event_data.arn,
          "${aws_s3_bucket.s3_event_data.arn}/*"
        ]
      },
      {
        Effect = "Allow",
        Action = [
          "rds-data:ExecuteStatement",
          "rds-data:BatchExecuteStatement",
          "rds-db:connect"
        ],
        Resource = [
          aws_db_instance.rds.arn
        ]
      },
      {
        Effect = "Allow",
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ],
        Resource = aws_secretsmanager_secret.rds_password_secret.arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "attach_essential_policies_to_lambda_role" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_essential_policies.arn
}

resource "aws_lambda_function" "lambda_store_backup" {
  function_name = "lambda_store_backup-${local.name_alias}"

  filename         = "${path.module}/lambda_store_backup/.output/lambda_handler.zip"
  layers           = [aws_lambda_layer_version.python_logging_layer.arn]
  source_code_hash = data.archive_file.zip_the_lambda_store_backup_code.output_base64sha256

  role    = aws_iam_role.lambda_store_backup_role.arn
  handler = "lambda_handler.lambda_handler"
  runtime = "python3.11"
  timeout = 300

  environment {
    variables = {
      S3_BACKUP_DATA = aws_s3_bucket.s3_backup_data.bucket
      S3_EVENT_DATA  = aws_s3_bucket.s3_event_data.bucket
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.attach_essential_policies_to_lambda_store_backup,
    aws_cloudwatch_log_group.lambda_store_backup_logs
  ]
}

data "archive_file" "zip_the_lambda_store_backup_code" {
  type        = "zip"
  source_dir  = "${path.module}/lambda_store_backup/src"
  output_path = "${path.module}/lambda_store_backup/.output/lambda_handler.zip"
}

resource "aws_cloudwatch_log_group" "lambda_store_backup_logs" {
  name              = "/aws/lambda/lambda_store_backup-${local.name_alias}"
  retention_in_days = 14
}


# IAM role and attachment
resource "aws_iam_role" "lambda_store_backup_role" {
  name = "lambda_store_backup_role-${local.name_alias}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Principal = {
          Service = "lambda.amazonaws.com"
        },
        Effect = "Allow"
      }
    ]
  })
}

resource "aws_iam_policy" "lambda_store_backup_data_policies" {
  name = "lambda_store_backup-policy-${local.name_alias}"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Resource = [
          "arn:aws:logs:${var.region_aws}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/lambda_store_backup-${local.name_alias}:*"
        ]
      },
      {
        Effect = "Allow",
        Action = [
          "s3:GetObject",
          "s3:ListBucket",
          "s3:DeleteObject"
        ],
        Resource = [
          aws_s3_bucket.s3_event_data.arn,
          "${aws_s3_bucket.s3_event_data.arn}/*"
        ]
      },
      {
        Effect = "Allow",
        Action = [
          "s3:PutObject",
          "s3:PutObjectAcl"
        ],
        Resource = [
          "${aws_s3_bucket.s3_backup_data.arn}/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "attach_essential_policies_to_lambda_store_backup" {
  role       = aws_iam_role.lambda_store_backup_role.name
  policy_arn = aws_iam_policy.lambda_store_backup_data_policies.arn
}
