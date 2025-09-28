resource "aws_lambda_function" "lambda_rest_api" {
  function_name = "lambda-rest-api-response-${local.name_alias}"

  filename         = "${path.module}/lambda_rest_api/.output/lambda_handler.zip"
  layers           = [aws_lambda_layer_version.python_pg8000_layer.arn, aws_lambda_layer_version.python_logging_layer.arn]
  source_code_hash = data.archive_file.zip_the_lambda_api_code.output_base64sha256

  role        = aws_iam_role.lambda_rest_api.arn
  handler     = "lambda_handler.lambda_handler"
  runtime     = "python3.8"
  timeout     = 90
  memory_size = 512

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
  retention_in_days = 7
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


resource "aws_iam_policy" "lambda_rest_api_policy" {
  name = "lambda_rest_api_policy-${local.name_alias}"

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
          "arn:aws:logs:${var.region_aws}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/lambda-rest-api-response-${local.name_alias}:*"
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
      {
        Effect = "Allow",
        Action = [
          "rds-db:connect"
        ],
        Resource = "arn:aws:rds-db:${var.region_aws}:${data.aws_caller_identity.current.account_id}:dbuser:${aws_db_instance.rds.id}/postgres"
      },
      {
        Effect = "Allow",
        Action = [
          "rds:DescribeDBInstances",
          "rds-data:ExecuteStatement"
        ],
        Resource = "*"
      },
      {
        Effect = "Allow",
        Action = [
          "lambda:InvokeFunction"
        ],
        Resource = "*"
      },
    ]
  })
}


# Attach the policy to the IAM role
resource "aws_iam_role_policy_attachment" "attach_policy" {
  role       = aws_iam_role.lambda_rest_api.name
  policy_arn = aws_iam_policy.lambda_rest_api_policy.arn
}

resource "aws_lambda_permission" "apigateway_lambda_invoke" {
  for_each = {
    for pair in setproduct(local.http_methods, keys(local.endpoints_list)) :
    "${pair[0]}-${pair[1]}" => {
      method = pair[0]
      path   = local.endpoints_list[pair[1]]
    }
  }

  statement_id  = "AllowExecutionFromAPIGateway-${each.key}"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.lambda_rest_api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.rest_api.execution_arn}/*/${each.value.method}${each.value.path}"
}

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


resource "random_password" "api_password" {
  length           = 16
  special          = true
  override_special = "_%@"
}

resource "aws_secretsmanager_secret" "api_password_secret" {
  name        = "api-token-authorisation-${local.name_alias}"
  description = "Reat Api access token ${local.name_alias}"
}

resource "aws_secretsmanager_secret_version" "api_password_secret_version" {
  secret_id     = aws_secretsmanager_secret.api_password_secret.id
  secret_string = jsonencode({ "password" = random_password.api_password.result })
}

resource "aws_api_gateway_rest_api" "rest_api" {
  name = "Rest-Api-${local.name_alias}"

  endpoint_configuration {
    types = ["REGIONAL"]
  }
}

locals {
  endpoints_list = {
    "orders"    = "/orders"
    "customers" = "/customers"
  }
  http_methods     = ["GET", "PUT"]
  integration_type = "AWS_PROXY"
}

# Create API Gateway Resources, Methods, and Integrations Dynamically
resource "aws_api_gateway_resource" "endpoints" {
  for_each = local.endpoints_list

  rest_api_id = aws_api_gateway_rest_api.rest_api.id
  parent_id   = aws_api_gateway_rest_api.rest_api.root_resource_id
  path_part   = each.key
}

resource "aws_api_gateway_method" "methods" {
  for_each = {
    for pair in setproduct(local.http_methods, keys(aws_api_gateway_resource.endpoints)) :
    "${pair[1]}-${pair[0]}" => {
      http_method  = pair[0]
      endpoint_key = pair[1]
      resource_id  = aws_api_gateway_resource.endpoints[pair[1]].id
      rest_api_id  = aws_api_gateway_resource.endpoints[pair[1]].rest_api_id
    }
  }

  rest_api_id   = each.value.rest_api_id
  resource_id   = each.value.resource_id
  http_method   = each.value.http_method
  authorization = "CUSTOM"
  authorizer_id = aws_api_gateway_authorizer.custom_authorizer.id

  request_parameters = merge( # make parameters optional
    {
      "method.request.header.Authorization" = true
    },
    contains(split("-", each.key), "customers") ? {
      "method.request.querystring.customer_id" = false
    } : {},
    contains(split("-", each.key), "orders") ? {
      "method.request.querystring.order_id" = false
    } : {}
  )
}


resource "aws_api_gateway_integration" "integrations" {
  for_each = aws_api_gateway_method.methods

  rest_api_id             = each.value.rest_api_id
  resource_id             = each.value.resource_id
  http_method             = each.value.http_method
  integration_http_method = "POST"
  type                    = local.integration_type
  uri                     = "arn:aws:apigateway:${var.region_aws}:lambda:path/2015-03-31/functions/${aws_lambda_function.lambda_rest_api.arn}/invocations"
}


# API Deployment
resource "aws_api_gateway_deployment" "api_deployment" {
  rest_api_id = aws_api_gateway_rest_api.rest_api.id
  stage_name  = "prod"
  triggers = {
    redeploy = "${timestamp()}" # Forces a new deployment on every apply
  }

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [
    aws_api_gateway_method.methods,
    aws_api_gateway_integration.integrations,
    aws_api_gateway_method_response.method_responses
  ]
}

resource "aws_api_gateway_method_response" "method_responses" {
  for_each = aws_api_gateway_method.methods

  rest_api_id = each.value.rest_api_id
  resource_id = each.value.resource_id
  http_method = each.value.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = true
  }

  response_models = {
    "application/json" = "Empty"
  }
}

resource "aws_api_gateway_integration_response" "integration_responses" {
  for_each = aws_api_gateway_method.methods

  rest_api_id = each.value.rest_api_id
  resource_id = each.value.resource_id
  http_method = each.value.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = "'*'"
  }

  depends_on = [
    aws_api_gateway_integration.integrations,
    aws_api_gateway_method_response.method_responses
  ]

}


resource "aws_api_gateway_authorizer" "custom_authorizer" {
  name                             = "Token-authorization-${local.name_alias}"
  rest_api_id                      = aws_api_gateway_rest_api.rest_api.id
  type                             = "TOKEN"
  authorizer_uri                   = "arn:aws:apigateway:${var.region_aws}:lambda:path/2015-03-31/functions/${aws_lambda_function.lambda_token_authorizer.arn}/invocations"
  authorizer_credentials           = aws_iam_role.lambda_rest_api.arn
  identity_source                  = "method.request.header.Authorization"
  authorizer_result_ttl_in_seconds = 0
}


resource "aws_cloudwatch_log_group" "api_gateway_logs" {
  name              = "/aws/apigateway/${aws_api_gateway_rest_api.rest_api.id}"
  retention_in_days = 7
}


resource "aws_iam_policy" "api_gateway_logging_policy" {
  name = "api-gateway-logging-policy"

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
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "attach_api_gateway_logging" {
  role       = aws_iam_role.lambda_rest_api.name
  policy_arn = aws_iam_policy.api_gateway_logging_policy.arn
}


# Enable CloudWatch Logs for API Gateway
resource "aws_api_gateway_account" "api_gateway_account" {
  cloudwatch_role_arn = aws_iam_role.api_gateway_cloudwatch_role.arn
}

# IAM Role for API Gateway to write to CloudWatch
resource "aws_iam_role" "api_gateway_cloudwatch_role" {
  name = "api-gateway-cloudwatch-role-${local.name_alias}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "apigateway.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

# Policy attachment for CloudWatch logging
resource "aws_iam_role_policy_attachment" "api_gateway_cloudwatch" {
  role       = aws_iam_role.api_gateway_cloudwatch_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs"
}

# Enable detailed logging for the API Gateway stage
resource "aws_api_gateway_method_settings" "all" {
  rest_api_id = aws_api_gateway_rest_api.rest_api.id
  stage_name  = aws_api_gateway_deployment.api_deployment.stage_name
  method_path = "*/*"

  settings {
    metrics_enabled    = true
    logging_level      = "INFO"
    data_trace_enabled = true
  }

  depends_on = [
    aws_api_gateway_account.api_gateway_account,
    aws_api_gateway_deployment.api_deployment
  ]
}