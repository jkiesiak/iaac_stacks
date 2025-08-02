import pulumi
import pulumi_aws as aws

def create_vpc():
    vpc = aws.ec2.Vpc("basic-vpc", cidr_block="10.0.0.0/16")
    pulumi.export("vpc_id", vpc.id)
