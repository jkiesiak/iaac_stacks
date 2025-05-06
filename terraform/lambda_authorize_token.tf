resource "aws_lambda_function" "lambda_token_authorizer" {
  function_name    = "lambda-token-authorizer-${local.name_alias}"
  filename         = "${path.module}/lambda_grant_token_access/.output/lambda_handler.zip"
  layers           = [aws_lambda_layer_version.python_logging_layer.arn]
  source_code_hash = data.archive_file.zip_the_lambda_token_access.output_base64sha256

  role    = aws_iam_role.lambda_authorize_token_role.arn
  handler = "lambda_handler.lambda_handler"
  runtime = "python3.8"

  environment {
    variables = {
      API_GATEWAY_TOKEN = aws_secretsmanager_secret.api_password_secret.name
      REGION            = var.region_aws
    }
  }
  depends_on = [
    aws_iam_role_policy_attachment.attach_essential_policies_to_lambda_authorize_token
  ]
}

data "archive_file" "zip_the_lambda_token_access" {
  type        = "zip"
  source_dir  = "${path.module}/lambda_grant_token_access/src"
  output_path = "${path.module}/lambda_grant_token_access/.output/lambda_handler.zip"
}


## IAM role and attachment
resource "aws_iam_role" "lambda_authorize_token_role" {
  name = "lambda_authorize_token-${local.name_alias}"

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

resource "aws_iam_policy" "lambda_authorize_token_policies" {
  name = "lambda_authorize_token-policy-${local.name_alias}"

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
          "arn:aws:logs:${var.region_aws}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/lambda-token-authorizer-${local.name_alias}:*"
        ]
      },
      {
        Effect = "Allow",
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ],
        Resource = [
          aws_secretsmanager_secret.api_password_secret.arn,
          aws_secretsmanager_secret.rds_password_secret.arn
        ]
      },
    ]
  })
}

resource "aws_iam_role_policy_attachment" "attach_essential_policies_to_lambda_authorize_token" {
  role       = aws_iam_role.lambda_authorize_token_role.name
  policy_arn = aws_iam_policy.lambda_authorize_token_policies.arn
}
