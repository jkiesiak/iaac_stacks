from typing import Optional

import pulumi
import pulumi_aws as aws
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
        self.igw = aws.ec2.InternetGateway(
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
        self.nat_eip = aws.ec2.Eip(
            resource_name=get_resource_name("nat-eip", env),
            opts=pulumi.ResourceOptions(parent=self),
        )

        self.nat_gateway = aws.ec2.NatGateway(
            resource_name=get_resource_name("nat-gw-public", env),
            allocation_id=self.nat_eip.id,
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
                tags={
                    **tags,
                    "Name": get_resource_name(f"private-subnet-{i + 1}", env),
                },
                opts=pulumi.ResourceOptions(parent=self),
            )
            self.private_subnets.append(subnet)

        self.public_route_table = aws.ec2.RouteTable(
            resource_name=get_resource_name("public-rt", env),
            vpc_id=self.vpc.id,
            tags={**tags, "Name": get_resource_name("public-rt", env)},
            opts=pulumi.ResourceOptions(parent=self),
        )

        aws.ec2.Route(
            resource_name=get_resource_name("public-rt-route", env),
            route_table_id=self.public_route_table.id,
            destination_cidr_block="0.0.0.0/0",
            gateway_id=self.igw.id,
            opts=pulumi.ResourceOptions(parent=self.public_route_table),
        )

        for i, public_subnet in enumerate(self.public_subnets):
            aws.ec2.RouteTableAssociation(
                resource_name=get_resource_name(f"public-rt-assoc-{i + 1}", env),
                subnet_id=public_subnet.id,
                route_table_id=self.public_route_table.id,
                opts=pulumi.ResourceOptions(parent=public_subnet),
            )

        # Private route table with route to NAT Gateway
        self.private_route_table = aws.ec2.RouteTable(
            resource_name=get_resource_name("private-rt", env),
            vpc_id=self.vpc.id,
            tags={**tags, "Name": get_resource_name("private-rt", env)},
            opts=pulumi.ResourceOptions(parent=self),
        )

        aws.ec2.Route(
            resource_name=get_resource_name("private-rt-route", env),
            route_table_id=self.private_route_table.id,
            destination_cidr_block="0.0.0.0/0",
            nat_gateway_id=self.nat_gateway.id,
            opts=pulumi.ResourceOptions(parent=self.private_route_table),
        )

        # Associate private subnets with this private route table
        for i, private_subnet in enumerate(self.private_subnets):
            aws.ec2.RouteTableAssociation(
                resource_name=get_resource_name(f"private-rt-assoc-{i + 1}", env),
                subnet_id=private_subnet.id,
                route_table_id=self.private_route_table.id,
                opts=pulumi.ResourceOptions(parent=private_subnet),
            )

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
                    description="Allow PostgreSQL access from any IP",
                ),
                aws.ec2.SecurityGroupIngressArgs(
                    protocol="tcp",
                    from_port=5432,
                    to_port=5432,
                    ipv6_cidr_blocks=["::/0"],
                    description="Allow PostgreSQL access from any IP",
                ),
            ],
            egress=[
                aws.ec2.SecurityGroupEgressArgs(
                    protocol="tcp",
                    from_port=5432,
                    to_port=5432,
                    cidr_blocks=[],
                    ipv6_cidr_blocks=["::/0"],
                    description="Allow PostgreSQL to IPv6",
                ),
                aws.ec2.SecurityGroupEgressArgs(
                    protocol="-1",
                    from_port=0,
                    to_port=0,
                    cidr_blocks=["0.0.0.0/0"],
                    description="Allow all outbound traffic",
                ),
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

        self.register_outputs(
            {
                "vpc_id": self.vpc.id,
                "rds_security_group_id": self.rds_security_group.id,
                "db_subnet_group": self.db_subnet_group.name,
            }
        )
