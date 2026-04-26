import json
import boto3
from botocore.exceptions import ClientError
from decimal import Decimal

REGION = "us-east-1"
TABLE_NAME = "music"
JSON_FILE = "2026a2_songs.json"


def load_json_file(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    if isinstance(data, dict) and "songs" in data and isinstance(data["songs"], list):
        return data["songs"]

    raise ValueError("JSON format invalid: 'songs' key not found or is not a list.")


def build_item(song):
    title = str(song["title"]).strip()
    artist = str(song["artist"]).strip()
    album = str(song["album"]).strip()
    year = int(song["year"])
    image_url = str(song["img_url"]).strip()

    item = {
        "artist": artist,
        #"year_album_title": f"{year}#{album}#{title}",
        "album_title": f"{album}#{title}",
        #"album_year_title": f"{album}#{year}#{title}",
        "year_title": f"{year}#{title}",
        "title": title,
        #"artist_album_year": f"{artist}#{album}#{year}",
        "artist_album": f"{artist}#{album}",
        #"year": Decimal(year),
        #"album": album,
        "image_url": image_url
    }

    return item


def insert_songs(table, songs):
    inserted_count = 0
    skipped_count = 0

    for song in songs:
        try:
            item = build_item(song)

            table.put_item(
                Item=item,
                ConditionExpression="attribute_not_exists(artist) AND attribute_not_exists(year_album_title)"
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
    dynamodb = boto3.resource("dynamodb", region_name=REGION)
    table = dynamodb.Table(TABLE_NAME)

    songs = load_json_file(JSON_FILE)
    insert_songs(table, songs)


if __name__ == "__main__":
    main()