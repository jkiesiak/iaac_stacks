import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_apigateway as apigateway,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_secretsmanager as secretsmanager,
    aws_logs as logs,
    CfnOutput,
    Duration,
    RemovalPolicy
)
from constructs import Construct
import json
import os
import random
import string


class ApiGatewayStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, rds_secret_name, rds_endpoint_address, rds_secret_arn, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Define locals
        name_alias = self.node.try_get_context("name_alias") or "default"

        # HTTP Methods and Endpoints
        http_methods = ["GET", "PUT"]
        endpoints_list = {
            "orders": "/orders",
            "customers": "/customers"
        }
        integration_type = apigateway.LambdaIntegrationOptions(
            proxy=True
        )

        # Generate a random password with only alphanumeric characters
        api_password = ''.join(
            random.choice(string.ascii_letters + string.digits + "_%@")
            for _ in range(16)
        )

        # Create Secrets Manager secret
        api_password_secret = secretsmanager.Secret(
            self, "ApiPasswordSecret",
            secret_name=f"api-token-authorisation-{name_alias}",
            description=f"Rest Api access token {name_alias}",
            secret_string_value=cdk.SecretValue.unsafe_plain_text(
                json.dumps({"password": api_password})
            ),
            removal_policy=RemovalPolicy.DESTROY
        )

        # Define Lambda Layers
        pg8000_layer = _lambda.LayerVersion(
            self, "Pg8000Layer",
            code=_lambda.Code.from_asset("dependencies/pg8000.zip"),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_8, _lambda.Runtime.PYTHON_3_9],
            layer_version_name="python_pg8000_layer"
        )

        logging_layer = _lambda.LayerVersion(
            self, "LoggingLayer",
            code=_lambda.Code.from_asset("dependencies/logging_layer.zip"),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_8, _lambda.Runtime.PYTHON_3_9],
            layer_version_name="python_logging_layer"
        )

        # Create API Gateway Rest API
        rest_api = apigateway.RestApi(
            self, "RestApi",
            rest_api_name=f"Rest-Api-{name_alias}",
            endpoint_types=[apigateway.EndpointType.REGIONAL],
            cloud_watch_role=True,
            deploy_options=apigateway.StageOptions(
                stage_name="prod",
                metrics_enabled=True,
                logging_level=apigateway.MethodLoggingLevel.INFO,
                data_trace_enabled=True
            )
        )

        # Lambda execution role with permissions
        _lambda_role = iam.Role(
            self, "LambdaRestApiRole",
            role_name=f"lambda_rest_api-{name_alias}",
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal("lambda.amazonaws.com"),
                iam.ServicePrincipal("apigateway.amazonaws.com")
            )
        )
        
        lambda_policy = iam.Policy(
            self, "LambdaRestApiPolicy",
            policy_name=f"lambda_rest_api_policy-{name_alias}",
            statements=[
                # CloudWatch Logs permission
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents"
                    ],
                    resources=[
                        f"arn:aws:logs:{self.region}:{self.account}:*"
                    ]
                ),

                # Secrets Manager permissions
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "secretsmanager:GetSecretValue",
                        "secretsmanager:DescribeSecret"
                    ],
                    resources=[
                        api_password_secret.secret_arn,
                        rds_secret_arn
                    ]
                ),

                # RDS Connect permission
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "rds-db:connect"
                    ],
                    resources=["*"]
                ),

                # RDS Describe and Data API Permissions
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "rds:DescribeDBInstances",
                        "rds-data:ExecuteStatement"
                    ],
                    resources=["*"]
                ),

                # Lambda Invoke Permissions
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "lambda:InvokeFunction"
                    ],
                    resources=["*"]
                )
            ]
        )

        # Attach the policy to the role
        lambda_policy.attach_to_role(_lambda_role)

        # TODO : update this fun /infra_stacks/cdk_stack_infrastructure/lambda_rest_api
        # Lambda functions
        _lambda_rest_api = _lambda.Function(
            self, "LambdaRestApi",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="lambda_handler.lambda_handler",
            code=_lambda.Code.from_asset("lambda_rest_api"),
            role=_lambda_role,
            environment={
                "SECRET_NAME": api_password_secret.secret_name,
                "RDS_SECRET_NAME": rds_secret_name,
                "DB_HOST": rds_endpoint_address,
            },
            layers=[pg8000_layer, logging_layer],
        )

        _lambda_token_authorizer = _lambda.Function(
            self, "LambdaTokenAuthorizer",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="lambda_handler.lambda_handler",
            code=_lambda.Code.from_asset("lambda_grant_token_access"),
            role=_lambda_role,
            environment={
                "SECRET_NAME": api_password_secret.secret_name
            }
        )

        # Grant lambda permission to read from Secrets Manager
        api_password_secret.grant_read(_lambda_token_authorizer)

        # Custom authorizer for API Gateway
        authorizer = apigateway.TokenAuthorizer(
            self, "CustomAuthorizer",
            handler=_lambda_token_authorizer,
            identity_source="method.request.header.Authorization",
            results_cache_ttl=Duration.seconds(0)
        )

        # Create resources and methods dynamically
        for endpoint_key, endpoint_path in endpoints_list.items():
            resource = rest_api.root.add_resource(endpoint_key)

            for method in http_methods:
                # Define the request parameters based on the endpoint
                request_params = {
                    "method.request.header.Authorization": True
                }

                if endpoint_key == "customers":
                    request_params["method.request.querystring.customer_id"] = False
                elif endpoint_key == "orders":
                    request_params["method.request.querystring.order_id"] = False

                # Add method with the custom authorizer
                resource.add_method(
                    method,
                    apigateway.LambdaIntegration(_lambda_rest_api),
                    request_parameters=request_params,
                    authorization_type=apigateway.AuthorizationType.CUSTOM,
                    authorizer=authorizer
                )

        # Outputs
        CfnOutput(self, "RestApiEndpoint", value=rest_api.url)
        CfnOutput(self, "ApiPasswordSecretName", value=api_password_secret.secret_name)
