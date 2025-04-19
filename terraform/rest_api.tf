resource "random_password" "api_password" {
  length           = 16
  special          = true
  override_special = "_%@"
}

resource "aws_secretsmanager_secret" "api_password_secret" {
  name        = "api-auth-password-${local.name_alias}"
  description = "Reat Api acess token ${local.name_alias}"
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
  http_method      = "GET"
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
  for_each = aws_api_gateway_resource.endpoints

  rest_api_id   = each.value.rest_api_id
  resource_id   = each.value.id
  http_method   = local.http_method
  authorization = "CUSTOM"
  authorizer_id = aws_api_gateway_authorizer.custom_authorizer.id

  depends_on = [aws_api_gateway_resource.endpoints]

  request_parameters = {
    "method.request.header.Authorization"    = true
    "method.request.querystring.customer_id" = false
    "method.request.querystring.order_id"    = false
  }
}

resource "aws_api_gateway_integration" "integrations" {
  for_each = aws_api_gateway_method.methods

  rest_api_id             = each.value.rest_api_id
  resource_id             = each.value.resource_id
  http_method             = each.value.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
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

# Enable Method Response (200 OK)
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

# Configure Integration Response Mapping
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
  name           = "Token-authorization-${local.name_alias}"
  rest_api_id    = aws_api_gateway_rest_api.rest_api.id
  type           = "TOKEN"
  authorizer_uri = "arn:aws:apigateway:${var.region_aws}:lambda:path/2015-03-31/functions/${aws_lambda_function.lambda_token_authorizer.arn}/invocations"

  #  authorizer_uri         = aws_lambda_function.lambda_token_authorizer.invoke_arn
  authorizer_credentials = aws_iam_role.lambda_rest_api.arn # Ensure Lambda role is used
  identity_source        = "method.request.header.Authorization"
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

# Add this to your existing configuration

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