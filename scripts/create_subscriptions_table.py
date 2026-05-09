import boto3
from botocore.exceptions import ClientError

# AWS region where DynamoDB table can create
REGION = "us-east-1"
# Table name
TABLE_NAME = "subscriptions"

# Source: GitHub Repository - Rachel Hagerman
# Adapted from: https://github.com/awsdocs/aws-doc-sdk-examples/blob/ee9be1b447b7036892505d36dea33b2e2409b422/python/example_code/dynamodb/GettingStarted/scenario_getting_started_movies.py#L101
# Modified for: creating subscriptions table


def create_subscriptions_table():
    """
    Creates the 'subscriptions' table in DynamoDB.
    This table tracks which users have subscribed to which songs, enabling the 
    'Subscription Area' functionality in the web application.
    
    The schema uses a 1:N relationship design where one email can be linked 
    to multiple song unique identifiers.
    """
    dynamodb = boto3.resource("dynamodb", region_name=REGION)

    try:
        table = dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[
                {"AttributeName": "email", "KeyType": "HASH"}, # Partition Key
                {"AttributeName": "song_key", "KeyType": "RANGE"} # Sort key - artist#album#title 
            ],
            AttributeDefinitions=[
                {"AttributeName": "email", "AttributeType": "S"},
                {"AttributeName": "song_key", "AttributeType": "S"}
                
            ],

            
            # Set the read/write capacity units
            ProvisionedThroughput={
                "ReadCapacityUnits": 5,
                "WriteCapacityUnits": 5
            }
        )

        print(f"Creating table '{TABLE_NAME}'...")
        table.wait_until_exists()
        print(f"Table '{TABLE_NAME}' created successfully.")

    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceInUseException":
            print(f"Table '{TABLE_NAME}' already exists.")
        else:
            print(e.response["Error"]["Message"])


if __name__ == "__main__":
    create_subscriptions_table()