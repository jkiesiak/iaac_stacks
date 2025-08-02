# import pulumi
# import pulumi_aws as aws
#
#
# class NetworkComponent:
#     def __init__(self, name: str, env: str):
#         self.env = env
#         resource_prefix = f"{name}-{env}"
#
#         # Use region or default to eu-west-1
#         aws_region = aws.config.region or "eu-west-1"
#         availability_zone = f"{aws_region}a"
#
#         # Unified tags
#         tags = {
#             "Environment": env,
#             "Project": name,
#         }
#
#         # VPC
#         self.vpc = aws.ec2.Vpc(
#             f"{resource_prefix}-vpc",
#             cidr_block="10.0.0.0/16",
#             enable_dns_support=True,
#             enable_dns_hostnames=True,
#             tags={**tags, "Name": f"{resource_prefix}-vpc"},
#         )
#
#         # Public Subnet
#         self.public_subnet = aws.ec2.Subnet(
#             f"{resource_prefix}-public-subnet",
#             vpc_id=self.vpc.id,
#             cidr_block="10.0.1.0/24",
#             availability_zone=availability_zone,
#             map_public_ip_on_launch=True,
#             tags={**tags, "Name": f"{resource_prefix}-public-subnet"},
#         )
#
#         # Private Subnet
#         self.private_subnet = aws.ec2.Subnet(
#             f"{resource_prefix}-private-subnet",
#             vpc_id=self.vpc.id,
#             cidr_block="10.0.2.0/24",
#             availability_zone=availability_zone,
#             map_public_ip_on_launch=False,
#             tags={**tags, "Name": f"{resource_prefix}-private-subnet"},
#         )
#
#         # Internet Gateway
#         self.igw = aws.ec2.InternetGateway(
#             f"{resource_prefix}-igw",
#             vpc_id=self.vpc.id,
#             tags={**tags, "Name": f"{resource_prefix}-igw"},
#         )
#
#         # Public Route Table
#         self.public_route_table = aws.ec2.RouteTable(
#             f"{resource_prefix}-public-rt",
#             vpc_id=self.vpc.id,
#             routes=[
#                 {
#                     "cidr_block": "0.0.0.0/0",
#                     "gateway_id": self.igw.id,
#                 }
#             ],
#             tags={**tags, "Name": f"{resource_prefix}-public-rt"},
#         )
#
#         aws.ec2.RouteTableAssociation(
#             f"{resource_prefix}-rt-assoc",
#             subnet_id=self.public_subnet.id,
#             route_table_id=self.public_route_table.id,
#         )
#
#         # Security Group for RDS
#         self.rds_sg = aws.ec2.SecurityGroup(
#             f"{resource_prefix}-rds-sg",
#             vpc_id=self.vpc.id,
#             description="Allow PostgreSQL access",
#             ingress=[
#                 {
#                     "protocol": "tcp",
#                     "from_port": 5432,
#                     "to_port": 5432,
#                     "cidr_blocks": ["0.0.0.0/0"],
#                     "ipv6_cidr_blocks": ["::/0"],
#                 }
#             ],
#             egress=[
#                 {
#                     "protocol": "-1",
#                     "from_port": 0,
#                     "to_port": 0,
#                     "cidr_blocks": ["0.0.0.0/0"],
#                 }
#             ],
#             tags={**tags, "Name": f"{resource_prefix}-rds-sg"},
#         )
#
#         # RDS Subnet Group
#         self.db_subnet_group = aws.rds.SubnetGroup(
#             f"{resource_prefix}-rds-subnet-group",
#             subnet_ids=[self.private_subnet.id],
#             tags={**tags, "Name": f"{resource_prefix}-rds-subnet-group"},
#         )
