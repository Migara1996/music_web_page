import boto3
from botocore.exceptions import ClientError

REGION = "us-east-1"
TABLE_NAME = "login"

# Replace these with your actual 10 records from image.png
LOGIN_ITEMS = [
    {"email": "s4111605@student.rmit.edu.au", "user_name": "MigaraVidanalage0", "password": "012345"},
    {"email": "s4111606@student.rmit.edu.au", "user_name": "DilrukshiPerera1", "password": "123456"},
    {"email": "s4111607@student.rmit.edu.au", "user_name": "SaumyaBandara2", "password": "234567"},
    {"email": "s4111608@student.rmit.edu.au", "user_name": "DinethraSigera3", "password": "345678"},
    {"email": "s4111609@student.rmit.edu.au", "user_name": "NudujaMapa4", "password": "646466"},
    {"email": "s4111610@student.rmit.edu.au", "user_name": "DeshaniAldeniya5", "password": "484614"},
    {"email": "s4111611@student.rmit.edu.au", "user_name": "EranGamage6", "password": "124688"},
    {"email": "s4111612@student.rmit.edu.au", "user_name": "AnushkaGedara7", "password": "955492"},
    {"email": "s4111613@student.rmit.edu.au", "user_name": "KelerraSilvester8", "password": "468781"},
    {"email": "s4111614@student.rmit.edu.au", "user_name": "SajanaFernando9", "password": "901234"},
]


def create_table_and_insert():
    dynamodb = boto3.resource("dynamodb", region_name=REGION)

    try:
        # Create table
        table = dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[
                {
                    "AttributeName": "email",
                    "KeyType": "HASH"
                }
            ],
            AttributeDefinitions=[
                {
                    "AttributeName": "email",
                    "AttributeType": "S"
                }
            ],
            ProvisionedThroughput={
                "ReadCapacityUnits": 5,
                "WriteCapacityUnits": 5
            }
        )

        print(f"Creating table '{TABLE_NAME}'...")
        table.wait_until_exists()
        print("Table created successfully.")

    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceInUseException":
            print("Table already exists. Using existing table.")
            table = dynamodb.Table(TABLE_NAME)
        else:
            print("Error creating table:")
            print(e.response["Error"]["Message"])
            return

    # Insert items
    print("Inserting items...")

    for item in LOGIN_ITEMS:
        try:
            table.put_item(
                Item=item,
                ConditionExpression="attribute_not_exists(email)"
            )
            print(f"Inserted: {item['email']}")
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                print(f"Skipped (already exists): {item['email']}")
            else:
                print("Error inserting item:")
                print(e.response["Error"]["Message"])

    print("Done.")


if __name__ == "__main__":
    create_table_and_insert()