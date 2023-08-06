module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "my-vpc-${local.name}"
  cidr = "10.0.0.0/16"

  azs             = ["eu-west-2a"]
  private_subnets = ["10.0.1.0/24"]
  public_subnets  = ["10.0.101.0/24"]

  create_database_subnet_group = true
  default_security_group_name = "security_group-${local.name}"
#  enable_nat_gateway = true
#  enable_vpn_gateway = true

  tags = {
    Terraform   = "true"
    Environment = "dev"
  }
}

#module "security_group" {
#  source  = "terraform-aws-modules/security-group/aws"
#  version = "~> 5.0"
#
#  name        = "security_group-${local.name}"
#  description = "Complete PostgreSQL example security group"
#  vpc_id      = module.vpc.vpc_id
#
#  # ingress
#  ingress_with_cidr_blocks = [
#    {
#      from_port   = 5432
#      to_port     = 5432
#      protocol    = "tcp"
#      description = "PostgreSQL access from within VPC"
#      cidr_blocks = module.vpc.vpc_cidr_block
#    },
#  ]
#}