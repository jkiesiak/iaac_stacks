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
  name               = "lambda_insert_data_into_rds-role-${local.name_alias}"
  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Effect": "Allow"
    }
  ]
}
EOF
}

resource "aws_iam_policy" "lambda_essential_policies" {
  name = "lambda_insert_data_into_rds-policy-${local.name_alias}"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      # Basic Lambda execution permissions
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
