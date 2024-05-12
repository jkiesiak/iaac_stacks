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
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF
}

resource "aws_iam_role_policy_attachment" "attach_iam_policy_to_iam_role" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3ObjectLambdaExecutionRolePolicy"
}

resource "aws_iam_role_policy_attachment" "attach_ssm_access_to_lambda_role" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMReadOnlyAccess"
}

resource "aws_iam_role_policy_attachment" "attach_s3_access_to_lambda_role" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}

data "archive_file" "zip_the_python_code" {
  type        = "zip"
  source_dir  = "${path.module}/lambda/src"
  output_path = "${path.module}/lambda/.output/lambda_handler.zip"
}

resource "aws_lambda_layer_version" "python_pg8000_layer" {
  filename   = "${path.module}/lambda/dependencies/pg8000.zip"
  layer_name = "python_pg8000_layer"

  compatible_runtimes = ["python3.8"]
}

resource "aws_lambda_function" "terraform_lambda_func" {
  function_name = "Lambda-Function-${local.name_alias}"

  filename         = "${path.module}/lambda/.output/lambda_handler.zip"
  layers           = [aws_lambda_layer_version.python_pg8000_layer.arn]
  source_code_hash = data.archive_file.zip_the_python_code.output_base64sha256

  role       = aws_iam_role.lambda_role.arn
  handler    = "lambda_handler.lambda_handler"
  runtime    = "python3.8"
  depends_on = [aws_iam_role_policy_attachment.attach_iam_policy_to_iam_role]

  environment {
    variables = {
      S3_BACKUP_DATA = aws_s3_bucket.s3_backup_data.bucket
      S3_EVENT_DATA  = aws_s3_bucket.s3_event_data.bucket
      RDS_HOST       = aws_db_instance.rds.address
      SSM_NAME       = aws_ssm_parameter.rds_password_parameter.name
      RDS_DB         = var.rds_database_name
    }
  }
}
