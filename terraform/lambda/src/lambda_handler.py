import os
import boto3
import pg8000
import json
import logging

S3_BACKUP_DATA = os.environ.get("S3_BACKUP_DATA")
S3_EVENT_DATA = os.environ.get("S3_EVENT_DATA")
RDS_HOST = os.environ.get("RDS_HOST")
RDS_DB = os.environ.get("RDS_DB")
RDS_USER = "postgres"
RDS_PORT = 5432
SSM_NAME = os.environ.get("SSM_NAME")

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    if not all([S3_BACKUP_DATA, S3_EVENT_DATA, RDS_HOST, RDS_DB, SSM_NAME]):
        raise ValueError("One or more required environment variables are missing.")

    secret = None
    response = None
    secrets_client = boto3.client("secretsmanager")
    secret = get_db_password(secrets_client)

    logger.info(f"Preprocessing data: {response}")


    # Initialize S3 client
    s3_client = boto3.client('s3')

    # Process the event
    logger.info(f"Processing data from bucket {S3_EVENT_DATA}")
    logger.info(f"Processing data from bucket event {event}")
    for record in event['Records']:
        file_name = record['s3']['object']['key']
        logger.info(f"Processing following file: {file_name}")

        try:
            response = s3_client.get_object(Bucket=S3_EVENT_DATA, Key=file_name)
            content = response['Body'].read().decode('utf-8')
            data = json.loads(content)
            logger.info(f"Processing following content: {data}")

            # Process data
            object_stored = False
            logger.info(f'Retrieving columns from data')
            if not data or not isinstance(data, list) or not all(isinstance(row, dict) for row in data):
                logger.error("Invalid input: 'data' must be a list of dictionaries with uniform keys.")
                return {
                    'statusCode': 500,
                    'body': json.dumps('Invalid data format. Please double-check the input.')
                }


            columns = list(data[0].keys())
            keys = set(data[0].keys())

            logger.info(f'Inferring TABLE NAME from data')
            if {"customer_id", "first_name", "last_name", "email", "phone", "address"}.issubset(keys):
                table_name = "customers"
                conflict_column = "customer_id"
            elif {"order_id", "order_date", "total_amount", "customer_id"}.issubset(keys):
                table_name = "orders"
                conflict_column = "order_id"
            else:
                raise ValueError("Unable to determine table name. Data keys do not match known schemas.")

            logger.info(f"Inserting data into table {table_name}")
            result = store_data_in_rds(
                db_host=RDS_HOST,
                db_port=RDS_PORT,
                db_user=RDS_USER,
                db_password=secret,
                db_name=RDS_DB,
                data=data,
                table_name=table_name,
                columns=columns,
                conflict_column=conflict_column
            )

            # Move object based on result
            if result:
                logger.info(f"Successfully inserted data into {table_name}. Moving file to backup.")
                move_file(s3_client, S3_EVENT_DATA, file_name, S3_BACKUP_DATA, f'backup/{file_name}')
            else:
                logger.error(f"Failed to insert data into {table_name}. Moving file to unprocessed.")
                move_file(s3_client, S3_EVENT_DATA, file_name, S3_BACKUP_DATA, f'unprocessed/{file_name}')

        except Exception as e:
            logger.error(f"Error processing file {file_name}: {e}")
            move_file(s3_client, S3_EVENT_DATA, file_name, S3_BACKUP_DATA, f'unprocessed/{file_name}')
            raise


    return {
        'statusCode': 200,
        'body': json.dumps('Processing complete')
    }


def get_db_password(secrets_client):
    """
    Generalized function to retrieve password for database.

    Args:
        secrets_client (str): Access to the Secret manager.

    Returns:
        SecretString: Returns password to the database.
    """
    try:
        response = secrets_client.get_secret_value(SecretId=SSM_NAME)
        secret = json.loads(response['SecretString'])
        logger.info("Database secret retrieved successfully.")
        return secret['password']
    except Exception as e:
        logger.error(f"Error retrieving secret: {secret}")
        raise


def store_data_in_rds(db_host, db_port, db_user, db_password, db_name, data, table_name, columns, conflict_column):
    """
    Store data in an RDS table.

    Args:
        db_host (str): Database host.
        db_port (int): Database port.
        db_user (str): Database username.
        db_password (str): Database password.
        db_name (str): Database name.
        data (list): List of dictionaries representing the rows to insert.
        table_name (str): Name of the target database table.
        columns (list): List of column names for insertion.
        conflict_column (str): Column to handle conflicts using ON CONFLICT.

    Returns:
        bool: True if data is successfully stored, False otherwise.
    """
    placeholders = ', '.join(['%s'] * len(columns))  # Generate placeholders dynamically
    column_names = ', '.join(columns)
    conflict_clause = f"ON CONFLICT ({conflict_column}) DO NOTHING"

    insert_query = f"""
        INSERT INTO myschema1.{table_name} ({column_names})
        VALUES ({placeholders})
        {conflict_clause};
    """

    try:
        # Connect to the database
        with pg8000.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            database=db_name
        ) as connection:
            with connection.cursor() as cursor:
                # Prepare data for bulk insertion
                rows = [tuple(row[col] for col in columns) for row in data]
                cursor.executemany(insert_query, rows)
                connection.commit()
                logger.info(f"Successfully stored {len(rows)} records in {table_name} table.")
        return True
    except Exception as e:
        logger.error(f"Error storing data in {table_name} table: {e}")
        return False


def move_file(s3_client, source_bucket, source_key, destination_bucket, destination_key):
    try:
        # Copy the file
        s3_client.copy_object(
            Bucket=destination_bucket,
            CopySource={'Bucket': source_bucket, 'Key': source_key},
            Key=destination_key
        )
        # Delete the original file
        s3_client.delete_object(Bucket=source_bucket, Key=source_key)
        logger.info(f"Successfully moved file from {source_bucket}/{source_key} to {destination_bucket}/{destination_key}.")
    except Exception as e:
        logger.error(f"Failed to move file {source_key} to {destination_key}: {e}")
        raise
