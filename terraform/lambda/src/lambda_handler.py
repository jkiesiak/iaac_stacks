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
    secrets_client = boto3.client("secretsmanager")
    secret = get_db_password(secrets_client)

    logger.info(f"Starting to process event data...")

    # Initialize S3 client
    s3_client = boto3.client('s3')

    for record in event['Records']:
        file_name = record['s3']['object']['key']
        logger.info(f"Processing file: {file_name}")
        move_directory = "unprocessed"  # Default directory in case of failure

        try:
            response = s3_client.get_object(Bucket=S3_EVENT_DATA, Key=file_name)
            content = response['Body'].read().decode('utf-8')
            data = json.loads(content)

            if not data or not isinstance(data, list) or not all(isinstance(row, dict) for row in data):
                logger.error("Invalid input: 'data' must be a list of dictionaries with uniform keys.")
                return {
                    'statusCode': 500,
                    'body': json.dumps(f"Invalid data format. Please double-check the input."
                                       f"Data = {data}")
                }

            # Determine the table name and column names
            columns = list(data[0].keys())
            keys = set(data[0].keys())

            logger.info(f"Inferring TABLE NAME from data")
            if {"customer_id", "first_name", "last_name", "email", "phone", "address"}.issubset(keys):
                table_name = "customers"
                conflict_column = "customer_id"
            elif {"order_id", "order_date", "total_amount", "customer_id"}.issubset(keys):
                table_name = "orders"
                conflict_column = "order_id"
            else:
                raise ValueError("Unable to determine table name. Data keys do not match known schemas.")

            # Insert data into RDS
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

            if result:
                logger.info(f"Successfully inserted data into {table_name}.")
                move_directory = "backup"  # Change to backup directory if successful
            else:
                logger.error(f"Failed to insert data into {table_name}.")

        except Exception as e:
            logger.error(f"Error processing file {file_name}: {e}")

        finally:
            # Move file to the appropriate directory
            move_file(s3_client, S3_EVENT_DATA, file_name, S3_BACKUP_DATA, f"{move_directory}/{file_name}")

    return {
        'statusCode': 200,
        'body': json.dumps('Processing complete')
    }


def get_db_password(secrets_client):
    try:
        response = secrets_client.get_secret_value(SecretId=SSM_NAME)
        secret = json.loads(response['SecretString'])
        logger.info("Database secret retrieved successfully.")
        return secret['password']
    except Exception as e:
        logger.error(f"Error retrieving secret: {e}")
        raise


def store_data_in_rds(db_host, db_port, db_user, db_password, db_name, data, table_name, columns, conflict_column):
    placeholders = ', '.join(['%s'] * len(columns))
    column_names = ', '.join(columns)
    conflict_clause = f"ON CONFLICT ({conflict_column}) DO NOTHING"

    insert_query = f"""
        INSERT INTO myschema1.{table_name} ({column_names})
        VALUES ({placeholders})
        {conflict_clause};
    """

    try:
        with pg8000.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            database=db_name
        ) as connection:
            with connection.cursor() as cursor:
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
