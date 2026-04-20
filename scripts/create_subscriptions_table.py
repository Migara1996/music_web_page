import boto3
from botocore.exceptions import ClientError

REGION = "us-east-1"
TABLE_NAME = "subscriptions"


def create_subscriptions_table():
    dynamodb = boto3.resource("dynamodb", region_name=REGION)

    try:
        table = dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[
                {"AttributeName": "email", "KeyType": "HASH"},
                {"AttributeName": "song_key", "KeyType": "RANGE"}
            ],
            AttributeDefinitions=[
                {"AttributeName": "email", "AttributeType": "S"},
                {"AttributeName": "song_key", "AttributeType": "S"}
            ],
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