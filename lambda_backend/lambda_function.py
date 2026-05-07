import json
import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
from decimal import Decimal
import re

REGION = "us-east-1"

# DynamoDB connection
dynamodb = boto3.resource("dynamodb", region_name=REGION)

# Tables
login_table = dynamodb.Table("login")
music_table = dynamodb.Table("music")
subscriptions_table = dynamodb.Table("subscriptions")


def response(status, body):
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Methods": "*"
        },
        "body": json.dumps(body)
    }


def convert_decimal(value):
    if isinstance(value, Decimal):
        if value % 1 == 0:
            return int(value)
        return float(value)
    return value


def serialize_item(item):
    if isinstance(item, dict):
        return {k: serialize_item(v) for k, v in item.items()}

    if isinstance(item, list):
        return [serialize_item(v) for v in item]

    return convert_decimal(item)

def login(event):
    try:
        data = json.loads(event.get("body") or "{}")

        email = data.get("email", "").strip()
        password = data.get("password", "").strip()

        if not email or not password:
            return response(400, {"message": "email or password is invalid"})

        db_response = login_table.get_item(Key={"email": email})
        user = db_response.get("Item")

        if not user:
            return response(401, {"message": "email or password is invalid"})

        if user.get("password") != password:
            return response(401, {"message": "email or password is invalid"})

        return response(200, {
            "message": "Login successful",
            "email": user["email"],
            "username": user["user_name"]
        })

    except ClientError as e:
        return response(500, {"message": e.response["Error"]["Message"]})
    
def register(event):
    try:
        data = json.loads(event.get("body") or "{}")

        email = data.get("email", "").strip()
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()

        if not email or not username or not password:
            return response(400, {"message": "All fields are required"})

        login_table.put_item(
            Item={
                "email": email,
                "user_name": username,
                "password": password
            },
            ConditionExpression="attribute_not_exists(email)"
        )

        return response(201, {"message": "User registered successfully"})

    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return response(409, {"message": "The email already exists"})

        return response(500, {"message": e.response["Error"]["Message"]})
    
def make_song_key(song):
    return f"{song['artist']}#{song['album']}#{song['title']}"


def subscribe(event):
    data = json.loads(event.get("body") or "{}")

    email = data.get("email", "").strip()
    title = data.get("title", "").strip()
    artist = data.get("artist", "").strip()
    album = data.get("album", "").strip()
    year = data.get("year")
    
    image_name = data.get("image_url", "").split("/")[-1]
    result = re.sub(r'(?<!^)(?=[A-Z])', '_', image_name)
    image_url = "https://a2-s3music-s.s3.us-east-1.amazonaws.com/artist-images/"+result

 # "Image   Name.jpg" → "Image_Name.jpg"

    if not email or not title or not artist or not album or year is None:
        return response(400, {"message": "Missing required subscription fields"})

    song = {
        "title": title,
        "artist": artist,
        "album": album,
        "year": int(year),
        "image_url": image_url
    }

    song_key = make_song_key(song)

    try:
        subscriptions_table.put_item(
            Item={
                "email": email,
                "song_key": song_key,
                "title": title,
                "artist": artist,
                "album": album,
                "year": int(year),
                "image_url": image_url
            },
            ConditionExpression="attribute_not_exists(email) AND attribute_not_exists(song_key)"
        )

        return response(201, {"message": "Song subscribed successfully"})

    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return response(409, {"message": "Song already subscribed"})
        return response(500, {"message": e.response["Error"]["Message"]})


def get_subscriptions(event):
    params = event.get("queryStringParameters") or {}
    email = params.get("email", "").strip()

    if not email:
        return response(400, {"message": "Email is required"})

    try:
        db_response = subscriptions_table.query(
            KeyConditionExpression=Key("email").eq(email)
        )

        items = [serialize_item(item) for item in db_response.get("Items", [])]

        return response(200, {"subscriptions": items})

    except ClientError as e:
        return response(500, {"message": e.response["Error"]["Message"]})


def remove_subscription(event):
    data = json.loads(event.get("body") or "{}")

    email = data.get("email", "").strip()
    title = data.get("title", "").strip()
    artist = data.get("artist", "").strip()

    if not email or not title or not artist:
        return response(400, {"message": "Email, title and artist are required"})

    try:
        db_response = subscriptions_table.query(
            KeyConditionExpression=Key("email").eq(email),
            FilterExpression=Attr("title").eq(title) & Attr("artist").eq(artist)
        )

        items = db_response.get("Items", [])

        if not items:
            return response(404, {"message": "Subscription not found"})

        subscription = items[0]

        subscriptions_table.delete_item(
            Key={
                "email": email,
                "song_key": subscription["song_key"]
            }
        )

        return response(200, {"message": "Subscription removed successfully"})

    except ClientError as e:
        return response(500, {"message": e.response["Error"]["Message"]})
    
def split_first(value):
    if not value or "#" not in value:
        return "", ""

    return value.split("#", 1)


def enrich_music_item(item):
    item = serialize_item(item)

    album, _ = split_first(item.get("album_title", ""))
    year, _ = split_first(item.get("year_title", ""))

    item["album"] = album
    item["year"] = int(year) if year.isdigit() else year

    return item

def query_music(event):

    params = event.get("queryStringParameters") or {}

    title = params.get("title", "").strip()
    year = params.get("year", "").strip()
    artist = params.get("artist", "").strip()
    album = params.get("album", "").strip()

    if not title and not year and not artist and not album:
        return response(400, {
            "message": "Please enter at least one search field."
        })

    try:
        items = []

        if artist:

            if album:
                db_response = music_table.query(
                    KeyConditionExpression=
                        Key("artist").eq(artist) &
                        Key("album_title").begins_with(f"{album}#")
                )

                items = db_response.get("Items", [])

            elif year:

                if title:
                    db_response = music_table.query(
                        IndexName="album-index",
                        KeyConditionExpression=
                            Key("artist").eq(artist) &
                            Key("year_title").eq(f"{year}#{title}")
                    )

                else:
                    db_response = music_table.query(
                        IndexName="album-index",
                        KeyConditionExpression=
                            Key("artist").eq(artist) &
                            Key("year_title").begins_with(f"{year}#")
                    )

                items = db_response.get("Items", [])

            else:
                db_response = music_table.query(
                    KeyConditionExpression=Key("artist").eq(artist)
                )

                items = db_response.get("Items", [])

        elif title:

            db_response = music_table.query(
                IndexName="title-index",
                KeyConditionExpression=Key("title").eq(title)
            )

            items = db_response.get("Items", [])

        else:
            db_response = music_table.scan()
            items = db_response.get("Items", [])

        filtered_items = []

        for item in items:

            enriched_item = enrich_music_item(item)

            match = True

            if title and enriched_item.get("title", "").lower() != title.lower():
                match = False

            if artist and enriched_item.get("artist", "").lower() != artist.lower():
                match = False

            if album and enriched_item.get("album", "").lower() != album.lower():
                match = False

            if year and str(enriched_item.get("year", "")) != str(year):
                match = False

            if match:
                filtered_items.append(enriched_item)

        if not filtered_items:
            return response(404, {
                "message": "No result is retrieved. Please query again",
                "results": []
            })

        return response(200, {
            "results": filtered_items
        })

    except ClientError as e:
        return response(500, {
            "message": e.response["Error"]["Message"]
        })
       
def lambda_handler(event, context):
    path = event["rawPath"]
    method = event["requestContext"]["http"]["method"]

    if path == "/login" and method == "POST":
        return login(event)

    if path == "/register" and method == "POST":
        return register(event)
    
    if path == "/subscribe" and method == "POST":
        return subscribe(event)

    if path == "/subscriptions" and method == "GET":
        return get_subscriptions(event)

    if path == "/remove" and method == "DELETE":
        return remove_subscription(event)
    
    if path == "/query" and method == "GET":
        return query_music(event)

    return response(200, {
        "message": "Lambda backend is running",
        "path": path,
        "method": method
    })