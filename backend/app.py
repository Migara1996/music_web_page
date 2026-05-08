from decimal import Decimal
from flask import Flask, request, jsonify # Import libraries of flask web framework
from flask_cors import CORS
import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

# Create the Flask application object.
app = Flask(__name__)

# Allow your frontend JavaScript to call this backend from another origin.
# This is useful during development when frontend and backend run on different URLs.
CORS(app)

# AWS region where DynamoDB tables and S3 bucket exist.
REGION = "us-east-1"

# AWS S3 image object path
S3_IMAGE_BASE_URL = "https://a2-s3music.s3.us-east-1.amazonaws.com/artist-images/"

# Source: AWS Boto3 Documentation
# Adapted from: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/dynamodb.html
# Modified for: connecting to music application tables

# Create a DynamoDB resource object.
# On EC2, boto3 can use the instance role credentials automatically if LabRole is attached.
dynamodb = boto3.resource("dynamodb", region_name=REGION)

# Reference the DynamoDB tables created earlier.
login_table = dynamodb.Table("login")
music_table = dynamodb.Table("music")
subscriptions_table = dynamodb.Table("subscriptions")


def convert_decimal(value):
    """
    DynamoDB returns numbers as Decimal.
    Flask's JSON response does not handle Decimal cleanly,
    so convert it to int or float before returning it.
    """
    if isinstance(value, Decimal):
        if value % 1 == 0:
            return int(value)
        return float(value)
    return value


def serialize_item(item):
    """
    Recursively convert any Decimal values inside dicts or lists
    so the response can be returned as JSON.
    """
    if isinstance(item, dict):
        return {k: serialize_item(v) for k, v in item.items()}
    if isinstance(item, list):
        return [serialize_item(v) for v in item]
    return convert_decimal(item)


def split_first(value):
    """
    Split a composite key value like 'album#title' or 'year#title'
    into two parts.
    """
    if not value or "#" not in value:
        return "", ""
    return value.split("#", 1)


def enrich_music_item(item):
    """
    music table does not store album and year separately.
    This function reconstructs album and year from:
    - album_title = album#title
    - year_title = year#title

    This keeps the frontend unchanged because frontend still expects:
    title, artist, album, year, image_url
    """
    item = serialize_item(item)

    album, _ = split_first(item.get("album_title", ""))
    year, _ = split_first(item.get("year_title", ""))

    item["album"] = album
    item["year"] = int(year) if year.isdigit() else year

    return item


def make_song_key(song):
    """
    Build a unique composite key for the subscriptions table.
    This helps prevent the same user subscribing to the same song multiple times.
    """
    return f"{song['artist']}#{song['album']}#{song['title']}"


def convert_to_s3_image_url(image_url):
    """
    Extract image name from image url and return it as S3 object url
    This function helps to access artist images from S3 bucket
    """
    image_name = image_url.split("/")[-1]    
    return S3_IMAGE_BASE_URL + image_name


# Backend running check for EC2
# @app.route("/", methods=["GET"])
# def home():
#     """
#     Simple health-check route.
#     Useful for confirming the backend is running on EC2.
#     """
#     return jsonify({"message": "EC2 Flask backend is running"}), 200

# Backend running check for ECS
@app.route("/", methods=["GET"])
def home():
    """
    Simple health-check route.
    Useful for confirming the backend is running on ECS.
    """
    return jsonify({"message": "ECS Flask backend is running"}), 200


# Source: Flask HTTP methods, handle GET & POST requests
# Adapted from: https://www.geeksforgeeks.org/python/flask-http-methods-handle-get-post-requests/
# Modified for: Make GET, POST & DELETE HTTP methods

@app.route("/login", methods=["POST"])
def login():
    """
    Validate user credentials against the login table.

    Expected request body:
    {
        "email": "...",
        "password": "..."
    }
    """
    data = request.get_json()

    if not data:
        return jsonify({"message": "Invalid request body"}), 400

    email = data.get("email", "").strip()
    password = data.get("password", "").strip()

    if not email or not password:
        return jsonify({"message": "email or password is invalid"}), 400

    try:
        # Read the user by primary key.
        response = login_table.get_item(Key={"email": email})
        user = response.get("Item")

        # User does not exist.
        if not user:
            return jsonify({"message": "email or password is invalid"}), 401

        # Password mismatch.
        if user.get("password") != password:
            return jsonify({"message": "email or password is invalid"}), 401

        # Login success.
        return jsonify({
            "message": "Login successful",
            "email": user["email"],
            "username": user["user_name"]
        }), 200

    except ClientError as e:
        return jsonify({"message": e.response["Error"]["Message"]}), 500


@app.route("/register", methods=["POST"])
def register():
    """
    Register a new user in the login table.

    Expected request body:
    {
        "email": "...",
        "username": "...",
        "password": "..."
    }

    Email must be unique.
    """
    data = request.get_json()

    if not data:
        return jsonify({"message": "Invalid request body"}), 400

    email = data.get("email", "").strip()
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if not email or not username or not password:
        return jsonify({"message": "All fields are required"}), 400

    try:
        # Conditional write prevents duplicate email registration.
        login_table.put_item(
            Item={
                "email": email,
                "user_name": username,
                "password": password
            },
            ConditionExpression="attribute_not_exists(email)"
        )

        return jsonify({"message": "User registered successfully"}), 201

    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return jsonify({"message": "The email already exists"}), 409

        return jsonify({"message": e.response["Error"]["Message"]}), 500


# Source: AWS Boto3 Documentation
# Adapted from: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/dynamodb.html
# Modified for: query and scan operations

@app.route("/query", methods=["GET"])
def query_music():
    """
    Query songs based on title, year, artist, and album.
    At least one field must be provided.

    music table schema:
    Base table:
        PK = artist
        SK = album_title  -> album#title

    LSI:
        PK = artist
        SK = year_title   -> year#title

    GSI:
        PK = title
        SK = artist_album -> artist#album
    """
    title = request.args.get("title", "").strip()
    year = request.args.get("year", "").strip()
    artist = request.args.get("artist", "").strip()
    album = request.args.get("album", "").strip()

    if not title and not year and not artist and not album:
        return jsonify({"message": "Please enter at least one search field."}), 400

    try:
        items = []

        if artist:
            if album:
                # Efficient query for artist + album using base table.
                response = music_table.query(
                    KeyConditionExpression=Key("artist").eq(artist) &
                    Key("album_title").begins_with(f"{album}#")
                )
                items = response.get("Items", [])

            elif year:
                # Efficient query for artist + year  & artist + year + title using LSI.
                                
                if title:
                    response = music_table.query(
                        IndexName="album-index", 
                        KeyConditionExpression=
                            Key("artist").eq(artist) &
                            Key("year_title").eq(f"{year}#{title}")
                    )

                # artist + year only
                else:
                    response = music_table.query(
                        IndexName="album-index",  
                        KeyConditionExpression=
                            Key("artist").eq(artist) &
                            Key("year_title").begins_with(f"{year}#")
                    )

                items = response.get("Items", [])

            else:
                # Efficient query for artist only.
                response = music_table.query(
                    KeyConditionExpression=Key("artist").eq(artist)
                )
                items = response.get("Items", [])

        elif title:
            # Efficient query for title using GSI.
            response = music_table.query(
                IndexName="title-index",
                KeyConditionExpression=Key("title").eq(title)
            )
            items = response.get("Items", [])

        else:
            # For album-only or year-only searches, use Scan.                        
            response = music_table.scan()
            items = response.get("Items", [])

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
                enriched_item["image_url"] = convert_to_s3_image_url(
                    enriched_item.get("image_url", "")
                )
                filtered_items.append(enriched_item)
                

        if not filtered_items:
            return jsonify({
                "message": "No result is retrieved. Please query again",
                "results": []
            }), 404

        return jsonify({"results": filtered_items}), 200

    except ClientError as e:
        return jsonify({"message": e.response["Error"]["Message"]}), 500



@app.route("/subscribe", methods=["POST"])
def subscribe():
    """
    Add a song to the user's subscription list.

    Expected request body:
    {
        "email": "...",
        "title": "...",
        "artist": "...",
        "album": "...",
        "year": 2008,
        "image_url": "..."
    }
    """
    data = request.get_json()

    if not data:
        return jsonify({"message": "Invalid request body"}), 400

    email = data.get("email", "").strip()
    title = data.get("title", "").strip()
    artist = data.get("artist", "").strip()
    album = data.get("album", "").strip()
    year = data.get("year")
    image_url = data.get("image_url", "").strip()

    if not email or not title or not artist or not album or year is None:
        return jsonify({"message": "Missing required subscription fields"}), 400

    song = {
        "title": title,
        "artist": artist,
        "album": album,
        "year": int(year),
        "image_url": image_url
    }

    song_key = make_song_key(song)

    try:
        # Prevent duplicate subscription by the same user for the same song.
        subscriptions_table.put_item(
            Item={
                "email": email,
                "song_key": song_key,
                #"album_title": f"{album}#{title}",
                "title": title,
                "artist": artist,
                "album": album,
                "year": int(year),
                "image_url": image_url
            },
            ConditionExpression="attribute_not_exists(email) AND attribute_not_exists(song_key)"
        )

        return jsonify({"message": "Song subscribed successfully"}), 201

    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return jsonify({"message": "Song already subscribed"}), 409

        return jsonify({"message": e.response["Error"]["Message"]}), 500


@app.route("/subscriptions", methods=["GET"])
def get_subscriptions():
    """
    Return all subscribed songs for a given user.

    Example:
    GET /subscriptions?email=user@example.com
    """
    email = request.args.get("email", "").strip()

    if not email:
        return jsonify({"message": "Email is required"}), 400

    try:
        response = subscriptions_table.query(
            KeyConditionExpression=Key("email").eq(email)
        )

        items = [serialize_item(item) for item in response.get("Items", [])]
        return jsonify({"subscriptions": items}), 200

    except ClientError as e:
        return jsonify({"message": e.response["Error"]["Message"]}), 500


@app.route("/remove", methods=["DELETE"])
def remove_subscription():
    """
    Remove one subscribed song for a given user.

    Expected request body:
    {
        "email": "...",
        "title": "...",
        "artist": "..."
    }

    We first find the matching row, then delete it using the table key.
    """
    data = request.get_json()

    if not data:
        return jsonify({"message": "Invalid request body"}), 400

    email = data.get("email", "").strip()
    title = data.get("title", "").strip()
    artist = data.get("artist", "").strip()

    if not email or not title or not artist:
        return jsonify({"message": "Email, title and artist are required"}), 400

    try:
        # Query all subscriptions for the user, then filter to the chosen song.
        response = subscriptions_table.query(
            KeyConditionExpression=Key("email").eq(email),
            FilterExpression=Attr("title").eq(title) & Attr("artist").eq(artist)
        )

        items = response.get("Items", [])

        if not items:
            return jsonify({"message": "Subscription not found"}), 404

        subscription = items[0]

        # Delete the exact item by its primary key.
        subscriptions_table.delete_item(
            Key={
                "email": email,
                "song_key": subscription["song_key"]
            }
        )

        return jsonify({"message": "Subscription removed successfully"}), 200

    except ClientError as e:
        return jsonify({"message": e.response["Error"]["Message"]}), 500


if __name__ == "__main__":
    # Debug mode is fine for local testing.
    # For EC2 & ECS production access, run with Gunicorn instead of flask run.
    app.run(host="0.0.0.0", port=5000, debug=True)