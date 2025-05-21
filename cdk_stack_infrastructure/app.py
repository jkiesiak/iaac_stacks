import aws_cdk as cdk

from stacks.step_functions_stack import LambdaRdsStack
from stacks.network import VpcStack
from stacks.rds_stack import RdsPostgresStack
from stacks.api_gateway import ApiGatewayStack

app = cdk.App()

name_alias = "polka"
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
                                rds_security_group=rds_security_group
                                )

rds_endpoint_address = rds_postgres.rds_endpoint_address
rds_secret_name = rds_postgres.rds_password_secret
rds_instance_id = rds_postgres.rds_instance_id
secret_arn = rds_postgres.secret_arn

LambdaRdsStack(app, "LambdaRdsStack",
               name_alias=name_alias,
               rds_instance_id = rds_instance_id,
               rds_endpoint_address=rds_endpoint_address,
               rds_secret_name=rds_secret_name,
               secret_arn=secret_arn
               )

# ApiGatewayStack(app, "ApiGatewayStack", name_alias=name_alias)
ApiGatewayStack(app, "ApiGatewayStack", rds_secret_name=rds_secret_name,rds_endpoint_address=rds_endpoint_address,rds_secret_arn=secret_arn)

app.synth()
