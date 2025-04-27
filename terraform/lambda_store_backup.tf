resource "aws_lambda_function" "lambda_store_backup" {
  function_name = "lambda_store_backup-${local.name_alias}"

  filename         = "${path.module}/lambda_store_backup/.output/lambda_handler.zip"
  layers           = [aws_lambda_layer_version.python_logging_layer.arn]
  source_code_hash = data.archive_file.zip_the_lambda_store_backup_code.output_base64sha256

  role    = aws_iam_role.lambda_role.arn
  handler = "lambda_handler.lambda_handler"
  runtime = "python3.8"
  timeout = 300

  environment {
    variables = {
      S3_BACKUP_DATA = aws_s3_bucket.s3_backup_data.bucket
      S3_EVENT_DATA  = aws_s3_bucket.s3_event_data.bucket
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.attach_essential_policies_to_lambda_store_backup
  ]
}

data "archive_file" "zip_the_lambda_store_backup_code" {
  type        = "zip"
  source_dir  = "${path.module}/lambda_store_backup/src"
  output_path = "${path.module}/lambda_store_backup/.output/lambda_handler.zip"
}



resource "aws_iam_role" "lambda_store_backup_role" {
  name               = "lambda_store_backup_role-${local.name_alias}"
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

resource "aws_iam_policy" "lambda_store_backup_data_policies" {
  name = "lambda_store_backup-policy-${local.name_alias}"

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
        "s3:DeleteObject",
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": "*"
    }
  ]
}
EOF
}

resource "aws_iam_role_policy_attachment" "attach_essential_policies_to_lambda_store_backup" {
  role       = aws_iam_role.lambda_store_backup_role.name
  policy_arn = aws_iam_policy.lambda_store_backup_data_policies.arn
}



