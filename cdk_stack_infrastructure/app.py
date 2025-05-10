import aws_cdk as cdk

from stacks.step_functions_stack import LambdaRdsStack

app = cdk.App()

data_storage_stack = LambdaRdsStack(app, "LambdaRdsStack")

app.synth()

