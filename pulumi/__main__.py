from components.network import VpcStack

vpc_stack = VpcStack(
    name="vpc-stack",
    env="dev",
)
