resource "aws_lambda_function" "lambda_rest_api" {
  function_name = "Lambda-Api-${local.name_alias}"

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
      RDS_HOST        = aws_db_instance.rds.address
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.attach_essential_policies_to_lambda_role
  ]
}

# Lambda Authorizer for API Gateway
resource "aws_api_gateway_authorizer" "custom_authorizer" {
  name                             = "Token-autorisation-${local.name_alias}"
  rest_api_id                      = aws_api_gateway_rest_api.rest_api.id
  authorizer_uri                   = "arn:aws:apigateway:${var.region_aws}:lambda:path/2015-03-31/functions/${aws_lambda_function.lambda_rest_api.arn}/invocations"
  authorizer_result_ttl_in_seconds = 300
  identity_source                  = "method.request.header.Authorization"
  type                             = "TOKEN"
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

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      # Allow access to Secrets Manager for retrieving secrets
      {
        Effect : "Allow",
        Action : [
          "secretsmanager:GetSecretValue"
        ],
        Resource : aws_secretsmanager_secret.api_password_secret.arn
      },
      # Allow Lambda to log to CloudWatch
      {
        Effect : "Allow",
        Action : [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Resource : "arn:aws:logs:*:*:*"
      },
      # (Optional) Allow access to RDS if Lambda needs it
      {
        Effect : "Allow",
        Action : [
          "rds:DescribeDBInstances",
          "rds:Connect"
        ],
        Resource : "*"
      },
      # Allow Lambda to be invoked by API Gateway
      {
        Effect : "Allow",
        Action : "lambda:InvokeFunction",
        Resource : aws_lambda_function.lambda_rest_api.arn
      }
    ]
  })
}

# Attach the policy to the IAM role
resource "aws_iam_role_policy_attachment" "attach_policy" {
  role       = aws_iam_role.lambda_rest_api.name
  policy_arn = aws_iam_policy.lambda_rest_api_policy.arn
}

resource "aws_lambda_permission" "apigateway_lambda_invoke" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.lambda_rest_api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.rest_api.execution_arn}/*"
}
