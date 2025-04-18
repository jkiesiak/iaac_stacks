resource "aws_lambda_function" "lambda_rest_api" {
  function_name = "lambda-rest-api-response-${local.name_alias}"

  filename         = "${path.module}/lambda_rest_api/.output/lambda_handler.zip"
  layers           = [aws_lambda_layer_version.python_pg8000_layer.arn, aws_lambda_layer_version.python_logging_layer.arn]
  source_code_hash = data.archive_file.zip_the_lambda_api_code.output_base64sha256

  role    = aws_iam_role.lambda_rest_api.arn
  handler = "lambda_handler.lambda_handler"
  runtime = "python3.8"
  timeout = 300

  environment {
    variables = {
      SECRET_NAME     = aws_secretsmanager_secret.api_password_secret.name
      RDS_SECRET_NAME = aws_secretsmanager_secret.rds_password_secret.name
      REGION          = var.region_aws
      DB_NAME         = var.rds_database_name
      DB_HOST         = aws_db_instance.rds.address
    }
  }
  depends_on = [
    aws_iam_role_policy_attachment.attach_policy,
    aws_cloudwatch_log_group.lambda_rest_api_logs
  ]
}

resource "aws_cloudwatch_log_group" "lambda_rest_api_logs" {
  name              = "/aws/lambda/lambda-rest-api-response-${local.name_alias}"
  retention_in_days = 14
}


data "archive_file" "zip_the_lambda_api_code" {
  type        = "zip"
  source_dir  = "${path.module}/lambda_rest_api/src"
  output_path = "${path.module}/lambda_rest_api/.output/lambda_handler.zip"
}


# IAM Role for Lambda
resource "aws_iam_role" "lambda_rest_api" {
  name = "lambda_rest_api-${local.name_alias}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          Service = ["lambda.amazonaws.com", "apigateway.amazonaws.com"]
        },
        Action = "sts:AssumeRole"
      }
    ]
  })
}

# IAM Policy for Lambda Permissions
resource "aws_iam_policy" "lambda_rest_api_policy" {
  name = "lambda_rest_api_policy-${local.name_alias}"

  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
          "logs:DescribeLogStreams",

        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket",
        "s3:DeleteObject",
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret",
        "rds:DescribeDBInstances",
        "rds:Connect",
        "lambda:InvokeFunction"
      ],
      "Resource": "*"
    }
  ]
}
EOF
}

# Attach the policy to the IAM role
resource "aws_iam_role_policy_attachment" "attach_policy" {
  role       = aws_iam_role.lambda_rest_api.name
  policy_arn = aws_iam_policy.lambda_rest_api_policy.arn
}

resource "aws_lambda_permission" "apigateway_lambda_invoke" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.lambda_rest_api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.rest_api.execution_arn}/*/*"
}

resource "aws_lambda_function" "lambda_token_authorizer" {
  function_name    = "lambda-token-authorizer-${local.name_alias}"
  filename         = "${path.module}/lambda_grant_token_access/.output/lambda_handler.zip"
  layers           = [aws_lambda_layer_version.python_pg8000_layer.arn, aws_lambda_layer_version.python_logging_layer.arn]
  source_code_hash = data.archive_file.zip_the_lambda_token_access.output_base64sha256

  role    = aws_iam_role.lambda_rest_api.arn
  handler = "lambda_handler.lambda_handler"
  runtime = "python3.8"

  environment {
    variables = {
      AUTH_TOKEN = random_password.api_password.result
    }
  }
}

data "archive_file" "zip_the_lambda_token_access" {
  type        = "zip"
  source_dir  = "${path.module}/lambda_grant_token_access/src"
  output_path = "${path.module}/lambda_grant_token_access/.output/lambda_handler.zip"
}
