import boto3
from botocore.exceptions import ClientError

# AWS region where DynamoDB table can create
REGION = "us-east-1"
# Table name
TABLE_NAME = "music"

# Source: GitHub Repository - Rachel Hagerman
# Adapted from: https://github.com/awsdocs/aws-doc-sdk-examples/blob/ee9be1b447b7036892505d36dea33b2e2409b422/python/example_code/dynamodb/GettingStarted/scenario_getting_started_movies.py#L101
# Modified for: creating music table and defining Primary key, LSI & GSI


def create_music_table():
    """
    Creates the 'music' table in DynamoDB with a composite primary key, 
    one Local Secondary Index (LSI), and one Global Secondary Index (GSI).
    
    The schema is designed to prevent data overwrites (lossless) and support 
    the specific query patterns required for the music subscription app.
    """
    dynamodb = boto3.resource("dynamodb", region_name=REGION)

    try:
        table = dynamodb.create_table(
            TableName=TABLE_NAME,

            # Composite Primary Key (Partition key + Sort key)
            KeySchema=[
                {
                    "AttributeName": "artist", # Partition key
                    "KeyType": "HASH"
                },
                {                    
                    "AttributeName": "album_title", # Sort key
                    "KeyType": "RANGE"
                }
            ],

            # Attributes
            AttributeDefinitions=[
                {"AttributeName": "artist", "AttributeType": "S"},                
                {"AttributeName": "album_title", "AttributeType": "S"},                
                {"AttributeName": "year_title", "AttributeType": "S"},
                {"AttributeName": "title", "AttributeType": "S"},                
                {"AttributeName": "artist_album", "AttributeType": "S"}
            ],

            # Local Secondary Index (LSI)
            LocalSecondaryIndexes=[
                {
                    "IndexName": "album-index",
                    "KeySchema": [
                        {"AttributeName": "artist", "KeyType": "HASH"}, # LSI PK must be the main PK
                        {"AttributeName": "year_title", "KeyType": "RANGE"} # LSI Sort Key
                    ],
                    "Projection": {
                        "ProjectionType": "ALL"
                    }
                }
            ],

            # Global Secondary Index (GSI)
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "title-index",
                    "KeySchema": [
                        {"AttributeName": "title", "KeyType": "HASH"}, # GSI PK
                        {"AttributeName": "artist_album", "KeyType": "RANGE"} # GSI SK
                    ],
                    "Projection": {
                        "ProjectionType": "ALL"
                    },
                    "ProvisionedThroughput": {
                        "ReadCapacityUnits": 5,
                        "WriteCapacityUnits": 5
                    }
                }
            ],
            # Set the read/write capacity units
            ProvisionedThroughput={
                "ReadCapacityUnits": 5,
                "WriteCapacityUnits": 5
            }
        )

        print("Creating 'music' table...")
        table.wait_until_exists()
        print("Music table created successfully.")

    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceInUseException":
            print("Table already exists.")
        else:
            print("Error creating table:")
            print(e.response["Error"]["Message"])


if __name__ == "__main__":
    create_music_table()