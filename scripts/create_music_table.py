import boto3
from botocore.exceptions import ClientError

REGION = "us-east-1"
TABLE_NAME = "music"

def create_music_table():
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
                    #"AttributeName": "year_album_title", # Sort key
                    "AttributeName": "album_title", # Sort key
                    "KeyType": "RANGE"
                }
            ],

            # Attributes
            AttributeDefinitions=[
                {"AttributeName": "artist", "AttributeType": "S"},
                #{"AttributeName": "year_album_title", "AttributeType": "S"},
                {"AttributeName": "album_title", "AttributeType": "S"},
                #{"AttributeName": "album_year_title", "AttributeType": "S"},
                {"AttributeName": "year_title", "AttributeType": "S"},
                {"AttributeName": "title", "AttributeType": "S"},
                #{"AttributeName": "artist_album_year", "AttributeType": "S"}
                {"AttributeName": "artist_album", "AttributeType": "S"}
            ],

            # Local Secondary Index (LSI)
            LocalSecondaryIndexes=[
                {
                    "IndexName": "album-index",
                    "KeySchema": [
                        {"AttributeName": "artist", "KeyType": "HASH"},
                        #{"AttributeName": "album_year_title", "KeyType": "RANGE"}
                        {"AttributeName": "year_title", "KeyType": "RANGE"}
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
                        {"AttributeName": "title", "KeyType": "HASH"},
                        #{"AttributeName": "artist_album_year", "KeyType": "RANGE"}
                        {"AttributeName": "artist_album", "KeyType": "RANGE"}
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