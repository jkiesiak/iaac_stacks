resource "aws_lambda_function" "lambda_data_preprocessing" {
  function_name = "Lambda-Function-${local.name_alias}"

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
  name               = "aws_lambda_role-${local.name_alias}"
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
  name = "LambdaEssentialPolicies-${local.name_alias}"

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
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket",
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": "*"
    }
  ]
}
EOF
}

resource "aws_iam_role_policy_attachment" "attach_essential_policies_to_lambda_role" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_essential_policies.arn
}

resource "aws_s3_bucket_notification" "event_trigger" {
  bucket = aws_s3_bucket.s3_event_data.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.lambda_data_preprocessing.arn
    events              = ["s3:ObjectCreated:*"]
  }

  depends_on = [aws_lambda_permission.allow_s3_event_trigger]
}

resource "aws_lambda_permission" "allow_s3_event_trigger" {
  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.lambda_data_preprocessing.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.s3_event_data.arn
}

resource "aws_security_group" "lambda_security_group" {
  name        = "lambda-security-group-${local.name_alias}"
  vpc_id      = module.vpc.vpc_id
  description = "Security group for Lambda to access RDS"

  egress {
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }
}

resource "aws_security_group_rule" "allow_lambda_to_rds" {
  security_group_id        = aws_security_group.lambda_security_group.id
  source_security_group_id = aws_security_group.rds_security_group.id
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
}




