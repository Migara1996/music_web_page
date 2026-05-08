import json
import boto3
from botocore.exceptions import ClientError
from decimal import Decimal

REGION = "us-east-1" # AWS region
TABLE_NAME = "music" # Table name
JSON_FILE = "2026a2_songs.json" # Music data file 


def load_json_file(file_path):
    """
    Opens and parses the local JSON file. Validates that the expected 'songs' 
    key exists and contains a list of data.
    
    Adapted from: Python Standard Library - json module documentation
    (https://docs.python.org/3/library/json.html)
    """
    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    if isinstance(data, dict) and "songs" in data and isinstance(data["songs"], list):
        return data["songs"]

    raise ValueError("JSON format invalid: 'songs' key not found or is not a list.")


def build_item(song):
    """
    Transforms raw JSON song data into a format that aligns with the DynamoDB schema.
    This creates composite attributes (using '#' as a delimiter) to support 
    advanced querying and prevent data loss.
    """
    title = str(song["title"]).strip()
    artist = str(song["artist"]).strip()
    album = str(song["album"]).strip()
    year = int(song["year"])
    image_url = str(song["img_url"]).strip()

    item = {
        "artist": artist,
        "album_title": f"{album}#{title}",
        "year_title": f"{year}#{title}",
        "title": title,
        "artist_album": f"{artist}#{album}",
        "image_url": image_url
    }

    return item


def insert_songs(table, songs):
    """
    Iterates through the list of songs and attempts to upload them to DynamoDB.
    Uses a ConditionExpression to ensure no data is accidentally overwritten.
    
    Adapted from: Boto3 Documentation - Table.put_item
    (https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb/table/put_item.html)
    """
    inserted_count = 0
    skipped_count = 0

    for song in songs:
        try:
            item = build_item(song)

            table.put_item(
                Item=item,
                ConditionExpression="attribute_not_exists(artist) AND attribute_not_exists(album_title)"
            )

            inserted_count += 1
            #print(f"Inserted: {item['artist']} | {item['year_album_title']}")
            print(f"Inserted: {item['artist']} | {item['album_title']}")
        except ClientError as e:
            error_code = e.response["Error"]["Code"]

            if error_code == "ConditionalCheckFailedException":
                skipped_count += 1
                print(
                    f"Skipped duplicate: {song['artist']} | "
                    #f"{song['year']}#{song['album']}#{song['title']}"
                    f"{song['album']}#{song['title']}"
                )
            else:
                skipped_count += 1
                print("Error inserting item:")
                print(e.response["Error"]["Message"])

        except KeyError as e:
            skipped_count += 1
            print(f"Skipped record due to missing field: {e}")

        except ValueError as e:
            skipped_count += 1
            print(f"Skipped record due to invalid value: {e}")

    print()
    print("Finished loading data.")
    print(f"Inserted: {inserted_count}")
    print(f"Skipped: {skipped_count}")


def main():
    """
    Initializes the Boto3 resource and orchestrates the data loading process.
    """
    dynamodb = boto3.resource("dynamodb", region_name=REGION)
    table = dynamodb.Table(TABLE_NAME)

    songs = load_json_file(JSON_FILE)
    insert_songs(table, songs)


if __name__ == "__main__":
    main()