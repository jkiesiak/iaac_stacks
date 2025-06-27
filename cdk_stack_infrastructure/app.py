from aws_cdk import App

from stacks.main_stack import MainStack

app = App()

env = app.node.try_get_context("environment")
region_aws = app.node.try_get_context("region_aws")
is_dev_raw = app.node.try_get_context("is_development")
is_dev = str(is_dev_raw).lower() == "true"


if not env:
    raise Exception("Missing context variable: env. Use 'cdk deploy -c env=dev'")

MainStack(app, f"MainStack-{env}", env, is_dev)

app.synth()
