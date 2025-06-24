from aws_cdk import App, Tags
from stacks.step_functions_stack import LambdaRdsStack
from stacks.network import VpcStack
from stacks.rds_stack import RdsPostgresStack
from stacks.api_gateway import ApiGatewayStack

region_aws = "eu-west-1"

app = App()

# Global tags
common_tags = {"Environment": "dev", "Project": "my-stack", "Owner": "Joanna Kiesiak"}

for key, value in common_tags.items():
    Tags.of(app).add(key, value)

vpc_stack = VpcStack(app, "VpcStack")
vpc = vpc_stack.vpc
rds_security_group = vpc_stack.rds_security_group

rds_postgres = RdsPostgresStack(
    app, "RDSStack", vpc=vpc, rds_security_group=rds_security_group
)
rds_endpoint_address = rds_postgres.rds_endpoint_address
rds_secret_name = rds_postgres.rds_password_secret
rds_instance_id = rds_postgres.rds_instance_id
secret_arn = rds_postgres.secret_arn

LambdaRdsStack(
    app,
    "LambdaRdsStack",
    rds_instance_id=rds_instance_id,
    rds_endpoint_address=rds_endpoint_address,
    rds_secret_name=rds_secret_name,
    secret_arn=secret_arn,
)

ApiGatewayStack(
    app,
    "ApiGatewayStack",
    rds_secret_name=rds_secret_name,
    rds_endpoint_address=rds_endpoint_address,
    rds_secret_arn=secret_arn,
)

app.synth()
