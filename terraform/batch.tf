resource "aws_ecs_cluster" "batch_cluster" {
  name = "batch-cluster-${local.name_alias}"
}

resource "aws_iam_role" "ecs_instance_role" {
  name = "ecs-instance-role-${local.name_alias}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Principal = {
          Service = "ec2.amazonaws.com",
        },
        Effect = "Allow",
        Sid    = "",
      },
    ],
  })
}

resource "aws_iam_role_policy_attachment" "ecs_instance_role" {
  role       = aws_iam_role.ecs_instance_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceforEC2Role"
}
resource "aws_iam_role" "aws_batch_service_role" {
  name = "aws-batch-service-role-${local.name_alias}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Principal = {
          Service = "batch.amazonaws.com",
        },
        Effect = "Allow",
        Sid    = "",
      },
    ],
  })
}


resource "aws_iam_instance_profile" "ecs_instance_profile" {
  name = "ecs-instance-profile-${local.name_alias}"
  role = aws_iam_role.ecs_instance_role.name
}


resource "aws_iam_role_policy_attachment" "aws_batch_service_role" {
  role       = aws_iam_role.aws_batch_service_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBatchServiceRole"
}
resource "aws_iam_role_policy_attachment" "aws_batch_full" {
  role       = aws_iam_role.aws_batch_service_role.name
  policy_arn = "arn:aws:iam::aws:policy/AWSBatchFullAccess"
}

resource "aws_batch_compute_environment" "sample_compute_env" {
  compute_environment_name = "sample-compute-environment-2-${local.name_alias}"
  compute_resources {
    instance_role = aws_iam_instance_profile.ecs_instance_profile.arn
    instance_type = ["m4.large"]
    max_vcpus     = 16
    min_vcpus     = 0
    type          = "EC2"
    security_group_ids = [
      aws_security_group.security_group.id,
    ]
    subnets = [aws_subnet.subnet_public_v1.id, aws_subnet.subnet_public_v2.id]
  }
  service_role = aws_iam_role.aws_batch_service_role.arn
  type         = "MANAGED"
  state        = "ENABLED"

}

resource "aws_iam_role" "aws_batch_execution_role" {
  name = "aws-batch-execution-role-${local.name_alias}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Principal = {
          Service = "ecs-tasks.amazonaws.com",
        },
        Effect = "Allow",
        Sid    = "",
      },
    ],
  })
}
resource "aws_iam_policy" "batch_logs_policy" {
  name        = "batch-logs-policy-${local.name_alias}"
  path        = "/logs/${local.name_alias}/"
  description = "IAM policy for logging from AWS Batch jobs"

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
      },
    ]
  })
}

resource "aws_iam_role_policy_attachment" "batch_execution_role_logs" {
  role       = aws_iam_role.aws_batch_execution_role.name
  policy_arn = aws_iam_policy.batch_logs_policy.arn
}

resource "aws_batch_job_queue" "sample_job_queue" {
  name     = "sample-job-queue-${local.name_alias}"
  priority = 1
  state    = "ENABLED"

  compute_environments = [
    aws_batch_compute_environment.sample_compute_env.arn,
  ]
}

resource "aws_batch_job_definition" "sample_job_definition" {
  name = "sample-job-definition2-${local.name_alias}"
  type = "container"
  #  platform_capabilities = ["FARGATE"]

  container_properties = jsonencode({
    image   = "${local.account_id}.dkr.ecr.${var.region_aws}.amazonaws.com/docker/${local.name_alias}:v0.1.2"
    memory  = 512
    vcpus   = 1
    command = ["python", "hello_world.py"]

    jobRoleArn : aws_iam_role.aws_batch_execution_role.arn,
    logConfiguration : {
      logDriver : "awslogs",
      options : {
        awslogs-group : "/aws/batch/job",
        awslogs-region : var.region_aws,
        awslogs-stream-prefix : "${local.name_alias}"
      }
    }
  })
}
