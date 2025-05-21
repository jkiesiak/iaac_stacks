import os
import json
import logging
import boto3

# Environment variables
API_GATEWAY_TOKEN = os.environ.get('SECRET_NAME')

logger = logging.getLogger()
logger.setLevel(logging.INFO)

client = boto3.client("secretsmanager")


def lambda_handler(event, context):
    if not all([API_GATEWAY_TOKEN]):
        raise ValueError("API_GATEWAY_TOKEN required environment variable is missing.")

    logger.info("Getting database crendentials...")
    correct_password = return_password_based_on_secret(API_GATEWAY_TOKEN)
    logger.info(f"event = {event}")

    # Extract and normalize token
    if 'authorizationToken' in event:
        token_value = event['authorizationToken']

        if isinstance(token_value, str):
            # If string, clean it and take the last part
            auth_token = token_value.strip().split()[-1]
        elif isinstance(token_value, list) and len(token_value) > 0:
            # If list, take the first element and clean it
            auth_token = str(token_value[0]).strip()

    if not auth_token:
        logger.warning("Missing Authorization token")
        return generate_policy('user', 'Deny', event.get('methodArn', '*'))

    # Validate authorization
    if auth_token == correct_password:
        logger.info("Authorization successful")
        return generate_policy('user', 'Allow', event['methodArn'])

    logger.warning("Authorization failed: Invalid token")
    return generate_policy('user', 'Deny', event['methodArn'])


def return_password_based_on_secret(NAME_SECRET):
    try:
        response = client.get_secret_value(SecretId=NAME_SECRET)
        secret = json.loads(response["SecretString"])
        logger.info("Database secret retrieved successfully.")
        return secret["password"]
    except Exception as e:
        logger.error(f"Error retrieving secret: {e}")
        raise


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
