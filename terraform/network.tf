module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "my-vpc-${local.name_alias}"
  cidr = "10.0.0.0/16"

  azs             = ["eu-west-2a"]
  private_subnets = ["10.0.1.0/24"]
  public_subnets  = ["10.0.101.0/24"]

  create_database_subnet_group = true
  default_security_group_name  = "security_group-${local.name_alias}"

  tags = {
    Terraform   = "true"
    Environment = "dev"
  }
}
