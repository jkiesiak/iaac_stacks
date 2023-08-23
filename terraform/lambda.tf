module "lambda_function" {
  source = "terraform-aws-modules/lambda/aws"

  function_name = "${local.name_alias}-partition-recording"
  description   = "Partition recordings on S3."
  environment_variables = {
    S3_BUCKET_NAME = aws_s3_bucket.s3_bucket.id
  }
  handler = "lambda_function.handler"

  create_package = true
  source_path = [
    {
      path           = "../lambda/"
      poetry_install = true
    }
  ]
  runtime     = "python3.10"
  memory_size = 256
  timeout     = 10

  attach_policies    = true
  number_of_policies = 1
  policies           = [aws_iam_policy.lambda_function.arn]
}

resource "aws_iam_policy" "lambda_function" {
  name   = "${local.name_alias}-partition-recording"
  policy = data.aws_iam_policy_document.lambda_function.json
}

data "aws_iam_policy_document" "lambda_function" {
  statement {
    actions = [
      "s3:ListBucket",
      "s3:GetObject",
      "s3:PutObject"
    ]
    resources = [
      "arn:aws:s3:::${aws_s3_bucket.s3_bucket.id}",
      "arn:aws:s3:::${aws_s3_bucket.s3_bucket.id}/*",
    ]
  }
}
