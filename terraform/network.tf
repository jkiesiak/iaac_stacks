resource "aws_vpc" "my_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = {
    Name = "my_vpc-${local.name_alias}"
  }
}

resource "aws_subnet" "subnet_public_v1" {
  vpc_id                  = aws_vpc.my_vpc.id
  cidr_block              = "10.0.9.0/24"
  availability_zone       = "${var.region_aws}a"
  map_public_ip_on_launch = true

  tags = {
    Name = "subnet_public_v1-${local.name_alias}"
  }
}

resource "aws_subnet" "subnet_public_v2" {
  vpc_id                  = aws_vpc.my_vpc.id
  cidr_block              = "10.0.10.0/24"
  availability_zone       = "${var.region_aws}b"
  map_public_ip_on_launch = true

  tags = {
    Name = "subnet_public_v2-${local.name_alias}"
  }
}

resource "aws_security_group" "security_group" {
  name        = "security_group_name-${local.name_alias}"
  description = "test rds module"
  vpc_id      = aws_vpc.my_vpc.id

  ingress {
    from_port        = 0
    to_port          = 0
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"]
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
    from_port        = 0
    to_port          = 0
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }
  egress {
    from_port        = 5432
    to_port          = 5432
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }
  tags = {
    Name = "security_group-${local.name_alias}"
  }
}

resource "aws_db_subnet_group" "subnet_group" {
  name       = "subnet_group-${local.name_alias}"
  subnet_ids = [aws_subnet.subnet_public_v1.id, aws_subnet.subnet_public_v2.id]

  tags = {
    Name = "subnet_group-${local.name_alias}"
  }
}

resource "aws_internet_gateway" "my_igw" {
  vpc_id = aws_vpc.my_vpc.id
  tags = {
    Name = "internet_gateway-${local.name_alias}"
  }
}

resource "aws_route_table" "public_subnet_route_table" {
  vpc_id = aws_vpc.my_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.my_igw.id
  }
  tags = {
    Name = "route_table-${local.name_alias}"
  }
}

resource "aws_route_table_association" "public_subnet_association_1" {
  subnet_id      = aws_subnet.subnet_public_v1.id
  route_table_id = aws_route_table.public_subnet_route_table.id
}

resource "aws_route_table_association" "public_subnet_association_2" {
  subnet_id      = aws_subnet.subnet_public_v2.id
  route_table_id = aws_route_table.public_subnet_route_table.id
}

