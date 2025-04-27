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
