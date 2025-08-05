from components.network import VpcStack
from components.rds import RdsStack
from components.step_functions import StepFunctionsStack

ENV = "dev"

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
    is_development=True,
)

# Create Step Functions workflow
step_fn_stack = StepFunctionsStack(
    name="stepfunctions",
    env=ENV,
    rds_instance_id=rds_stack.rds_instance_id,
    rds_endpoint_address=rds_stack.rds_endpoint,
    rds_secret_name=rds_stack.rds_secret_name,
    rds_secret_arn=rds_stack.secret_arn,
)
