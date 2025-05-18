import boto3
import pg8000
import json
import os
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    """Lambda handler for PostgreSQL schema setup"""
    logger.info(f"Received event type: {event.get('RequestType', 'direct invocation')}")

    # Simple handling for CloudFormation events
    if event.get('RequestType') == 'Delete':
        logger.info("Delete request received, nothing to do")
        return {"Status": "SUCCESS"}

    if event.get('RequestType') not in [None, 'Create', 'Update']:
        logger.info(f"Unsupported RequestType: {event.get('RequestType')}")
        return {"Status": "SUCCESS"}

    # Get environment variables
    try:
        secret_name = os.environ["SECRET_NAME"]
        db_host = os.environ["DB_HOST"]

        if not all([db_host, secret_name]):
            error_msg = "One or more required environment variables are empty."
            logger.error(error_msg)
            return {"Status": "FAILED", "Reason": error_msg}

    except KeyError as e:
        error_msg = f"Missing required environment variable: {str(e)}"
        logger.error(error_msg)
        return {"Status": "FAILED", "Reason": error_msg}

    # Get secret
    try:
        client = boto3.client("secretsmanager")
        secret_value = client.get_secret_value(SecretId=secret_name)
        secret = json.loads(secret_value["SecretString"])
        logger.info("Retrieved database credentials from Secret Manager")
    except Exception as e:
        error_msg = f"Failed to retrieve secret: {str(e)}"
        logger.error(error_msg)
        return {"Status": "FAILED", "Reason": error_msg}

    # Extract credentials safely
    try:
        username = secret["username"]
        password = secret["password"]
        host = secret.get("host", db_host)  # Use secret host if available, otherwise env var
        port = int(secret.get("port", 5432))
        logger.info(f"Connecting to PostgreSQL at {host}:{port} as {username}")
    except KeyError as e:
        error_msg = f"Missing required credential in secret: {str(e)}"
        logger.error(error_msg)
        return {"Status": "FAILED", "Reason": error_msg}

    # First connection - check if database exists and create if needed
    first_conn = None
    try:
        first_conn = pg8000.connect(
            user=username,
            password=password,
            host=host,
            database="postgres",  # Connect to default database first
            port=port
        )
        first_conn.autocommit = True

        cursor = first_conn.cursor()
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = 'database_rds'")
        exists = cursor.fetchone()

        if not exists:
            logger.info("Creating database 'database_rds'...")
            cursor.execute("CREATE DATABASE database_rds;")
            logger.info("Database 'database_rds' created successfully")
        else:
            logger.info("Database 'database_rds' already exists")

        cursor.close()

    except Exception as e:
        error_msg = f"Failed to create/check database: {str(e)}"
        logger.error(error_msg)
        return {"Status": "FAILED", "Reason": error_msg}
    finally:
        if first_conn:
            first_conn.close()
            logger.info("First connection closed")

    # Second connection - apply schema to the database
    second_conn = None
    try:
        logger.info("Connecting to 'database_rds' to apply schema...")
        second_conn = pg8000.connect(
            user=username,
            password=password,
            host=host,
            database="database_rds",
            port=port
        )

        cursor = second_conn.cursor()

        schema_sql = """
        CREATE SCHEMA IF NOT EXISTS myschema1;
        SET search_path TO myschema1,public;

        CREATE TABLE IF NOT EXISTS myschema1.customers (
            customer_id SERIAL PRIMARY KEY,
            first_name VARCHAR(50),
            last_name VARCHAR(50),
            email VARCHAR(100),
            phone VARCHAR(15),
            address VARCHAR(100)
        );

        CREATE TABLE IF NOT EXISTS myschema1.orders (
            order_id SERIAL PRIMARY KEY,
            order_date DATE,
            total_amount DECIMAL(10, 2),
            customer_id INTEGER REFERENCES myschema1.customers(customer_id)
            -- Removed duplicate FOREIGN KEY constraint
        );
        """

        logger.info("Executing schema SQL...")
        cursor.execute(schema_sql)
        second_conn.commit()
        logger.info("Schema applied successfully")

        cursor.close()

        # Return simple success response
        return {"Status": "SUCCESS", "Message": "Database and schema created successfully"}
    except Exception as e:
        error_msg = f"Failed to apply schema: {str(e)}"
        logger.error(error_msg)
        return {"Status": "FAILED", "Reason": error_msg}
    finally:
        if second_conn:
            second_conn.close()
            logger.info("Second connection closed")
