import pulumi

from components.network import VpcStack
from components.rds import RdsStack
from components.step_functions import StepFunctionsStack
from components.api_gateway import ApiGatewayStack

config = pulumi.Config("my-infra")
ENV = config.require("env")
is_dev = config.get_bool("is_development") or False

vpc_stack = VpcStack(
    name="vpc-stack",
    env=ENV,
)

rds_stack = RdsStack(
    name="rds",
    env=ENV,
    vpc_id=vpc_stack.vpc.id,
    subnet_ids=[subnet.id for subnet in vpc_stack.public_subnets],
    rds_security_group_id=vpc_stack.rds_security_group.id,
    is_development=is_dev,
)

step_fn_stack = StepFunctionsStack(
    name="stepfunctions",
    env=ENV,
    rds_instance_arn=rds_stack.rds_instance_arn,
    rds_endpoint_address=rds_stack.rds_endpoint,
    rds_secret_name=rds_stack.rds_secret_name,
    rds_secret_arn=rds_stack.secret_arn,
)

ApiGatewayStack(
    "apiGatewayStack",
    env=ENV,
    rds_secret_name=rds_stack.rds_secret_name,
    rds_endpoint_address=rds_stack.rds_endpoint,
    rds_secret_arn=rds_stack.secret_arn,
    pg8000_layer_arn=step_fn_stack.pg8000_layer,
    logging_layer_arn=step_fn_stack.logging_layer,
)
