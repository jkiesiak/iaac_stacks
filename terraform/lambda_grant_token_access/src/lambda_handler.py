import os
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    logger.info("Received API Gateway request")

    # Retrieve expected token from environment
    EXPECTED_TOKEN = os.environ.get('AUTH_TOKEN')

    if not EXPECTED_TOKEN:
        logger.error("AUTH_TOKEN environment variable is not set")
        raise ValueError("Environment variable AUTH_TOKEN is not set")

    # Extract and normalize token
    auth_header = event.get('authorizationToken', '').strip().split()

    if auth_header:
        token = auth_header[-1] # token is always the last str
    else:
        logger.warning("Invalid Authorization header format")
        return generate_policy('user', 'Deny', event.get('methodArn', '*'))

    # Validate authorization
    if token == EXPECTED_TOKEN:
        logger.info("Authorization successful")
        return generate_policy('user', 'Allow', event['methodArn'])

    logger.warning("Authorization failed: Invalid token")
    return generate_policy('user', 'Deny', event['methodArn'])


def generate_policy(principal_id, effect, resource):
    if not effect or not resource:
        logger.error("Invalid policy generation attempt: Missing effect/resource")
        raise ValueError("Invalid policy: effect and resource are required")

    logger.info(f"Generating {effect} policy for resource: {resource}")

    return {
        'principalId': principal_id,
        'policyDocument': {
            'Version': '2012-10-17',
            'Statement': [{
                'Action': 'execute-api:Invoke',
                'Effect': effect,
                'Resource': resource
            }]
        }
    }
