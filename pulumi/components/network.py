import pulumi
import pulumi_aws as aws
from typing import Optional, List

from naming_utils import get_resource_name
from .tags import get_common_tags


class VpcStack(pulumi.ComponentResource):
    def __init__(
        self,
        name: str,
        env: str,
        cidr_block: Optional[str] = "10.0.0.0/16",
        opts: Optional[pulumi.ResourceOptions] = None,
    ):
        super().__init__("custom:VpcStack", name, None, opts)

        tags = get_common_tags(env)

        # Use the first 2 available AZs
        azs = aws.get_availability_zones(state="available").names
        selected_azs = azs[:2]

        # VPC
        self.vpc = aws.ec2.Vpc(
            resource_name=get_resource_name("vpc", env),
            cidr_block=cidr_block,
            enable_dns_hostnames=True,
            enable_dns_support=True,
            tags={**tags, "Name": get_resource_name("vpc", env)},
            opts=pulumi.ResourceOptions(parent=self),
        )

        # Internet Gateway
        igw = aws.ec2.InternetGateway(
            resource_name=get_resource_name("igw", env),
            vpc_id=self.vpc.id,
            tags={**tags, "Name": get_resource_name("igw", env)},
            opts=pulumi.ResourceOptions(parent=self),
        )

        # Public Subnet
        self.public_subnets = []
        for i, az in enumerate(selected_azs):
            subnet = aws.ec2.Subnet(
                resource_name=get_resource_name(f"public-subnet-{i + 1}", env),
                vpc_id=self.vpc.id,
                cidr_block=f"10.0.{i + 1}.0/24",
                availability_zone=az,
                map_public_ip_on_launch=True,
                tags={**tags, "Name": get_resource_name(f"public-subnet-{i + 1}", env)},
                opts=pulumi.ResourceOptions(parent=self),
            )
            self.public_subnets.append(subnet)

        # NAT Gateway
        nat_eip = aws.ec2.Eip(
            resource_name=get_resource_name("nat-eip", env),
            opts=pulumi.ResourceOptions(parent=self),
        )

        self.nat_gateway = aws.ec2.NatGateway(
            resource_name=get_resource_name("nat-gw", env),
            allocation_id=nat_eip.id,
            subnet_id=self.public_subnets[0].id,
            tags={**tags, "Name": get_resource_name("nat-gw", env)},
            opts=pulumi.ResourceOptions(parent=self),
        )

        # Private Subnet
        self.private_subnets = []
        for i, az in enumerate(selected_azs):
            subnet = aws.ec2.Subnet(
                resource_name=get_resource_name(f"private-subnet-{i + 1}", env),
                vpc_id=self.vpc.id,
                cidr_block=f"10.0.{i + 11}.0/24",
                availability_zone=az,
                map_public_ip_on_launch=False,
                tags={**tags, "Name": get_resource_name(f"private-subnet-{i + 1}", env)},
                opts=pulumi.ResourceOptions(parent=self),
            )
            self.private_subnets.append(subnet)

        # RDS Security Group
        self.rds_security_group = aws.ec2.SecurityGroup(
            resource_name=get_resource_name("rds-sg", env),
            description="Security group for RDS instance",
            vpc_id=self.vpc.id,
            ingress=[
                aws.ec2.SecurityGroupIngressArgs(
                    protocol="tcp",
                    from_port=5432,
                    to_port=5432,
                    cidr_blocks=["0.0.0.0/0"],
                    ipv6_cidr_blocks=["::/0"],
                    description="Allow PostgreSQL access from any IP",
                )
            ],
            egress=[
                aws.ec2.SecurityGroupEgressArgs(
                    protocol="tcp",
                    from_port=5432,
                    to_port=5432,
                    cidr_blocks=[],
                    ipv6_cidr_blocks=["::/0"],
                    description="Allow PostgreSQL to IPv6",
                )
            ],
            tags={**tags, "Name": get_resource_name("rds-sg", env)},
            opts=pulumi.ResourceOptions(parent=self),
        )

        # DB Subnet Group (use public subnet just like before, though not typical)
        self.db_subnet_group = aws.rds.SubnetGroup(
            resource_name=get_resource_name("subnet-group", env),
            subnet_ids=[subnet.id for subnet in self.public_subnets],
            description="Subnet group for RDS instance",
            tags={**tags, "Name": get_resource_name("subnet-group", env)},
            opts=pulumi.ResourceOptions(parent=self),
        )

        self.register_outputs({
            "vpc_id": self.vpc.id,
            "rds_security_group_id": self.rds_security_group.id,
            "db_subnet_group": self.db_subnet_group.name,
        })
