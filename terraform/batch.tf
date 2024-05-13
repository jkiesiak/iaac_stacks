#resource "aws_ecs_cluster" "batch_cluster" {
#  name = "batch-cluster-${local.name_alias}"
#}
#
#resource "aws_iam_role" "aws_batch_service_role" {
#  name = "aws-batch-service-role-${local.name_alias}"
#
#  assume_role_policy = jsonencode({
#    Version = "2012-10-17",
#    Statement = [
#      {
#        Action = "sts:AssumeRole",
#        Principal = {
#          "Service" : [
#            "ec2.amazonaws.com",
#            "ecr.amazonaws.com",
#            "ecs-tasks.amazonaws.com",
#            "batch.amazonaws.com"
#        ] },
#        Effect = "Allow",
#      },
#    ],
#  })
#}
#
#resource "aws_iam_role_policy_attachment" "ecs_instance_role" {
#  role       = aws_iam_role.aws_batch_service_role.id
#  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
#}
#
#resource "aws_iam_role_policy_attachment" "aws_batch_service_role" {
#  role       = aws_iam_role.aws_batch_service_role.name
#  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBatchServiceRole"
#}
#
#resource "aws_iam_role_policy_attachment" "ecs_task_execution_role_policy" {
#  role       = aws_iam_role.aws_batch_service_role.name
#  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
#}
#
#resource "aws_iam_role_policy_attachment" "cloudwatch_logs_policy_attachment" {
#  role       = aws_iam_role.aws_batch_service_role.name
#  policy_arn = "arn:aws:iam::aws:policy/CloudWatchLogsFullAccess"
#}
#
#resource "aws_iam_role_policy_attachment" "ecr_read_policy_attachment" {
#  role       = aws_iam_role.aws_batch_service_role.name
#  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly" #AmazonEC2ContainerRegistryFullAccess
#}
#resource "aws_batch_compute_environment" "sample_compute_env" {
#  compute_environment_name = "sample-compute-environment-${local.name_alias}"
#  compute_resources {
#    type               = "FARGATE"
#    security_group_ids = [aws_security_group.epc_security_endpoints.id]
#    subnets            = [for subnet in module.vpc.public_subnets : subnet]
#    max_vcpus          = 16
#
#  }
#
#  service_role = aws_iam_role.aws_batch_service_role.arn
#  depends_on   = [aws_iam_role_policy_attachment.aws_batch_service_role]
#
#  type  = "MANAGED"
#  state = "ENABLED"
#
#}
#
#resource "aws_batch_job_queue" "sample_job_queue" {
#  name     = "sample-job-queue-${local.name_alias}"
#  priority = 1
#  state    = "ENABLED"
#
#  compute_environments = [aws_batch_compute_environment.sample_compute_env.arn]
#}
#
#resource "aws_batch_job_definition" "sample_job_definition" {
#  name                  = "job-definition-${local.name_alias}"
#  type                  = "container"
#  platform_capabilities = ["FARGATE"]
#
#  container_properties = jsonencode({
#    image   = "${aws_ecr_repository.my_repository.repository_url}:v0.1.6"
#    command = ["python", "lambda/hello_world.py"]
#
#    jobRoleArn = aws_iam_role.aws_batch_service_role.arn
#    fargatePlatformConfiguration = {
#      platformVersion = "LATEST"
#    }
#    networkConfiguration = {
#      "assignPublicIp" : "ENABLED"
#    }
#    resourceRequirements = [
#      {
#        type  = "VCPU",
#        value = "0.25"
#      },
#      {
#        type  = "MEMORY",
#        value = "512"
#      }
#    ]
#    environment = [
#      {
#        name  = "RDS_HOST",
#        value = aws_db_instance.rds.address
#      },
#      {
#        name  = "RDS_PASSWORD",
#        value = random_password.rds_password.result
#      },
#      {
#        name  = "S3_BUCKET_NAME",
#        value = aws_s3_bucket.s3_bucket.bucket
#      },
#      {
#        name  = "SQS_QUEUE_URL",
#        value = aws_batch_job_queue.sample_job_queue.name
#      }
#    ]
#    logConfiguration : {
#      logDriver : "awslogs",
#      options : {
#        awslogs-group : aws_cloudwatch_log_group.log_group.name
#        awslogs-region : var.region_aws,
#        awslogs-stream-prefix : local.name_alias
#      }
#    }
#    executionRoleArn = aws_iam_role.aws_batch_service_role.arn
#
#  })
#
#  timeout {
#    attempt_duration_seconds = 60
#  }
#}
#
#resource "aws_cloudwatch_log_group" "log_group" {
#  name = "/aws/batch/${local.name_alias}"
#}