from aws_cdk import Stack, Tags
from constructs import Construct
from stacks.network import VpcStack
from stacks.rds_stack import RdsPostgresStack
from stacks.step_functions_stack import LambdaRdsStack
from stacks.api_gateway import ApiGatewayStack
from datetime import datetime


class MainStack(Stack):
    def __init__(self, scope: Construct, id: str, env: str, is_development: bool, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        self.env = env
        self.is_development = is_development
        Tags.of(self).add("Environment", self.env)
        Tags.of(self).add("Project", "my-stack")
        Tags.of(self).add("Owner", "Joanna Kiesiak")
        deployment_time = datetime.utcnow().isoformat()
        Tags.of(self).add("DeploymentTime", deployment_time)

        vpc_stack = VpcStack(self, f"VpcStack-{env}", env=env)
        vpc = vpc_stack.vpc
        rds_security_group = vpc_stack.rds_security_group

        rds_postgres = RdsPostgresStack(
            self,
            f"RDSStack-{env}",
            vpc=vpc,
            rds_security_group=rds_security_group,
            env=env,
            is_development=self.is_development
        )
        rds_endpoint_address = rds_postgres.rds_endpoint_address
        rds_secret_name = rds_postgres.rds_password_secret
        rds_instance_id = rds_postgres.rds_instance_id
        secret_arn = rds_postgres.secret_arn

        LambdaRdsStack(
            self,
            f"LambdaRdsStack-{env}",
            rds_instance_id=rds_instance_id,
            rds_endpoint_address=rds_endpoint_address,
            rds_secret_name=rds_secret_name,
            secret_arn=secret_arn,
            env=env
        )

        ApiGatewayStack(
            self,
            f"ApiGatewayStack-{env}",
            rds_secret_name=rds_secret_name,
            rds_endpoint_address=rds_endpoint_address,
            rds_secret_arn=secret_arn,
            env=env
        )
