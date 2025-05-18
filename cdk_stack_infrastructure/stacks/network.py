from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_rds as rds,
)
from constructs import Construct

class VpcStack(Stack):

    def __init__(self, scope: Construct, id: str, *, region_aws: str, name_alias: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        # availability zones
        azs = [f"{region_aws}a", f"{region_aws}b"]

        # Create the VPC
        vpc = ec2.Vpc(self, f"MyVpc-{name_alias}",
            # vpc_name=f"my_vpc-module-{name_alias}",
            cidr="10.0.0.0/16",
            max_azs=2,
            nat_gateways=1,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24
                ),
            ],
            enable_dns_hostnames=True,
            enable_dns_support=True
        )

        # Security Group for RDS
        rds_sg = ec2.SecurityGroup(self, f"RdsSecurityGroup{name_alias}",
            vpc=vpc,
            # security_group_name=f"vpc-security-group-{name_alias}",
            allow_all_outbound=True
        )

        # Ingress rules
        rds_sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(5432), "Allow PostgreSQL access from IPv4")
        rds_sg.add_ingress_rule(ec2.Peer.any_ipv6(), ec2.Port.tcp(5432), "Allow PostgreSQL access from IPv6")

        # Egress rules
        # rds_sg.add_egress_rule(ec2.Peer.any_ipv4(), ec2.Port.all_traffic(), "Allow all outbound IPv4")
        rds_sg.add_egress_rule(ec2.Peer.any_ipv6(), ec2.Port.tcp(5432), "Allow PostgreSQL to IPv6")
        # rds_sg.add_egress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(5432), "Allow PostgreSQL to any_ipv4")

        # DB Subnet Group (using public subnets like in Terraform, though private is more typical for RDS)
        db_subnet_group = rds.CfnDBSubnetGroup(self, "DbSubnetGroup",
            db_subnet_group_description="Subnet group for RDS instance",
            subnet_ids=[subnet.subnet_id for subnet in vpc.public_subnets],
            db_subnet_group_name=f"my-rds-subnet-group-{name_alias}"
        )

        # Outputs if needed
        self.vpc = vpc
        self.rds_security_group = rds_sg
        self.db_subnet_group = db_subnet_group
