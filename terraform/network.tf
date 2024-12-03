module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.5.3"

  name = "my_vpc-module-${local.name_alias}"
  cidr = "10.0.0.0/16"

  azs                     = ["${var.region_aws}a", "${var.region_aws}b"]
  private_subnets         = ["10.0.1.0/24", "10.0.2.0/24"]
  public_subnets          = ["10.0.101.0/24", "10.0.102.0/24"]
  map_public_ip_on_launch = true #needed for batch jobs to map public ip address

  create_database_subnet_group           = true
  create_database_subnet_route_table     = true
  create_database_internet_gateway_route = true

  enable_nat_gateway = true
  single_nat_gateway = true
  enable_vpn_gateway = false

}


resource "aws_security_group" "rds_security_group" {
  name   = "vpc-security-group-${local.name_alias}"
  vpc_id = module.vpc.vpc_id


  ingress {
    from_port        = 5432
    to_port          = 5432
    protocol         = "tcp"
    ipv6_cidr_blocks = ["::/0"]
  }

  ingress {
    from_port        = 5432
    to_port          = 5432
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }


  egress {
    from_port        = 5432
    to_port          = 5432
    protocol         = "tcp"
    ipv6_cidr_blocks = ["::/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

}

resource "aws_db_subnet_group" "rds_subnet_group" {
  name        = "my-rds-subnet-group-${local.name_alias}"
  description = "Subnet group for RDS instance"
  subnet_ids  = [for subnet in module.vpc.public_subnets : subnet]
}
