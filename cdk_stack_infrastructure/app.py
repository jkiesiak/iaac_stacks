import aws_cdk as cdk

from stacks.step_functions_stack import LambdaRdsStack
from stacks.network import VpcStack
from stacks.rds_stack import RdsPostgresStack

app = cdk.App()

name_alias = "aga"
region_aws = "eu-west-1"

vpc_stack = VpcStack(app, "VpcStack",
                     region_aws=region_aws,
                     name_alias=name_alias)

vpc = vpc_stack.vpc
rds_security_group = vpc_stack.rds_security_group
# db_subnet_group = vpc_stack.db_subnet_group

rds_postgres = RdsPostgresStack(app, "RDSStack",
                                name_alias=name_alias,
                                vpc=vpc,
                                rds_security_group=rds_security_group,
                                # db_subnet_group="public"
                                )

rds_endpoint_address = rds_postgres.rds_endpoint_address
rds_secret_name = rds_postgres.rds_password_secret

LambdaRdsStack(app, "LambdaRdsStack",
               name_alias=name_alias,
               rds_endpoint_address=rds_endpoint_address,
               rds_secret_name=rds_secret_name
               )

app.synth()
