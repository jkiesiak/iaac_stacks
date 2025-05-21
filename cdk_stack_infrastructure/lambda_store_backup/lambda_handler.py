import os
import boto3
import logging

S3_EVENT_DATA = os.environ.get("S3_EVENT_DATA")
S3_BACKUP_DATA = os.environ.get("S3_BACKUP_DATA")

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    if not all([S3_EVENT_DATA, S3_BACKUP_DATA]):
        raise ValueError("One or more required environment variables are missing.")

    logger.info("Starting to process files...")
    s3_client = boto3.client('s3')

    logger.info(f"Event looks following: {event}")
    if 'body' in event:
        file_name = event['body']['object_key']
    else:
        raise ValueError("Unsupported event format")

    logger.info(f"Processing file: {file_name}")
    try:
            # Move file to destination bucket
        move_file(
                s3_client,
                S3_EVENT_DATA,
                file_name,
                S3_BACKUP_DATA,
                file_name  # Keeping the same key in destination
            )
    except Exception as e:
        logger.error(f"Error processing file {file_name}: {e}")
        raise

        return {
        'statusCode': 200,
        'body': 'File movement complete'
        }


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
        logger.info(
            f"Successfully moved file from {source_bucket}/{source_key} to {destination_bucket}/{destination_key}.")
    except Exception as e:
        logger.error(f"Failed to move file {source_key} to {destination_key}: {e}")
        raise