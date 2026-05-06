import json
import boto3
from decimal import Decimal
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

REGION = "us-east-1"

dynamodb = boto3.resource("dynamodb", region_name=REGION)
login_table = dynamodb.Table("login")
music_table = dynamodb.Table("music")
subscriptions_table = dynamodb.Table("subscriptions")

# CORS headers required for browser-based frontend calls.
# Access-Control-Allow-Origin should be restricted to the S3 frontend
# domain in production rather than wildcard.
CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "GET,POST,DELETE,OPTIONS",
}


def respond(status_code, body):
    return {
        "statusCode": status_code,
        "headers": CORS_HEADERS,
        "body": json.dumps(body, default=_decimal_default),
    }


def _decimal_default(obj):
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def serialize_item(item):
    if isinstance(item, dict):
        return {k: serialize_item(v) for k, v in item.items()}
    if isinstance(item, list):
        return [serialize_item(v) for v in item]
    if isinstance(item, Decimal):
        return int(item) if item % 1 == 0 else float(item)
    return item


def _split_first(value):
    """Split a composite key like 'album#title' into (album, title)."""
    if not value or "#" not in value:
        return "", ""
    return value.split("#", 1)


def enrich_music_item(item):
    """
    Reconstruct album and year from composite sort keys so the frontend
    always receives: title, artist, album, year, image_url.
    """
    item = serialize_item(item)
    album, _ = _split_first(item.get("album_title", ""))
    year, _ = _split_first(item.get("year_title", ""))
    item["album"] = album
    item["year"] = int(year) if year.isdigit() else year
    return item


def make_song_key(song):
    """Unique composite key for a subscription row."""
    return f"{song['artist']}#{song['album']}#{song['title']}"


def _get_param(params, key):
    """Safely extract a query-string value whether it arrives as str or list."""
    val = params.get(key, "")
    if isinstance(val, list):
        val = val[0] if val else ""
    return val.strip()


# ──────────────────────────────────────────────────────────────────────────────
# Route handlers
# ──────────────────────────────────────────────────────────────────────────────

def handle_login(body):
    if not body:
        return respond(400, {"message": "Invalid request body"})

    email = body.get("email", "").strip()
    password = body.get("password", "").strip()

    if not email or not password:
        return respond(400, {"message": "email or password is invalid"})

    try:
        response = login_table.get_item(Key={"email": email})
        user = response.get("Item")

        if not user:
            return respond(401, {"message": "email or password is invalid"})

        if user.get("password") != password:
            return respond(401, {"message": "email or password is invalid"})

        return respond(200, {
            "message": "Login successful",
            "email": user["email"],
            "username": user["user_name"],
        })

    except ClientError as e:
        return respond(500, {"message": e.response["Error"]["Message"]})


def handle_register(body):
    if not body:
        return respond(400, {"message": "Invalid request body"})

    email = body.get("email", "").strip()
    username = body.get("username", "").strip()
    password = body.get("password", "").strip()

    if not email or not username or not password:
        return respond(400, {"message": "All fields are required"})

    try:
        login_table.put_item(
            Item={"email": email, "user_name": username, "password": password},
            ConditionExpression="attribute_not_exists(email)",
        )
        return respond(201, {"message": "User registered successfully"})

    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return respond(409, {"message": "The email already exists"})
        return respond(500, {"message": e.response["Error"]["Message"]})


def handle_query(params):
    title = _get_param(params, "title")
    year = _get_param(params, "year")
    artist = _get_param(params, "artist")
    album = _get_param(params, "album")

    if not title and not year and not artist and not album:
        return respond(400, {"message": "Please enter at least one search field."})

    try:
        items = []

        if artist:
            if album:
                # Base table query: artist (PK) + album#title prefix (SK).
                response = music_table.query(
                    KeyConditionExpression=Key("artist").eq(artist)
                    & Key("album_title").begins_with(f"{album}#"),
                )
                items = response.get("Items", [])

            elif year:
                # LSI query: artist (PK) + year#title prefix or exact (SK).
                if title:
                    response = music_table.query(
                        IndexName="album-index",
                        KeyConditionExpression=Key("artist").eq(artist)
                        & Key("year_title").eq(f"{year}#{title}"),
                    )
                else:
                    response = music_table.query(
                        IndexName="album-index",
                        KeyConditionExpression=Key("artist").eq(artist)
                        & Key("year_title").begins_with(f"{year}#"),
                    )
                items = response.get("Items", [])

            else:
                # All songs by artist.
                response = music_table.query(
                    KeyConditionExpression=Key("artist").eq(artist)
                )
                items = response.get("Items", [])

        elif title:
            # GSI query: title (PK).
            response = music_table.query(
                IndexName="title-index",
                KeyConditionExpression=Key("title").eq(title),
            )
            items = response.get("Items", [])

        else:
            # Album-only or year-only: no key path available, use Scan.
            response = music_table.scan()
            items = response.get("Items", [])

        filtered = []
        for item in items:
            enriched = enrich_music_item(item)
            match = True

            if title and enriched.get("title", "").lower() != title.lower():
                match = False
            if artist and enriched.get("artist", "").lower() != artist.lower():
                match = False
            if album and enriched.get("album", "").lower() != album.lower():
                match = False
            if year and str(enriched.get("year", "")) != str(year):
                match = False

            if match:
                filtered.append(enriched)

        if not filtered:
            return respond(404, {
                "message": "No result is retrieved. Please query again",
                "results": [],
            })

        return respond(200, {"results": filtered})

    except ClientError as e:
        return respond(500, {"message": e.response["Error"]["Message"]})


def handle_get_subscriptions(params):
    email = _get_param(params, "email")

    if not email:
        return respond(400, {"message": "Email is required"})

    try:
        response = subscriptions_table.query(
            KeyConditionExpression=Key("email").eq(email)
        )
        items = [serialize_item(i) for i in response.get("Items", [])]
        return respond(200, {"subscriptions": items})

    except ClientError as e:
        return respond(500, {"message": e.response["Error"]["Message"]})


def handle_subscribe(body):
    if not body:
        return respond(400, {"message": "Invalid request body"})

    email = body.get("email", "").strip()
    title = body.get("title", "").strip()
    artist = body.get("artist", "").strip()
    album = body.get("album", "").strip()
    year = body.get("year")
    image_url = body.get("image_url", "").strip()

    if not email or not title or not artist or not album or year is None:
        return respond(400, {"message": "Missing required subscription fields"})

    song = {"title": title, "artist": artist, "album": album,
            "year": int(year), "image_url": image_url}
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
                "image_url": image_url,
            },
            ConditionExpression="attribute_not_exists(email) AND attribute_not_exists(song_key)",
        )
        return respond(201, {"message": "Song subscribed successfully"})

    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return respond(409, {"message": "Song already subscribed"})
        return respond(500, {"message": e.response["Error"]["Message"]})


def handle_remove_subscription(body):
    if not body:
        return respond(400, {"message": "Invalid request body"})

    email = body.get("email", "").strip()
    title = body.get("title", "").strip()
    artist = body.get("artist", "").strip()

    if not email or not title or not artist:
        return respond(400, {"message": "Email, title and artist are required"})

    try:
        response = subscriptions_table.query(
            KeyConditionExpression=Key("email").eq(email),
            FilterExpression=Attr("title").eq(title) & Attr("artist").eq(artist),
        )
        items = response.get("Items", [])

        if not items:
            return respond(404, {"message": "Subscription not found"})

        subscriptions_table.delete_item(
            Key={"email": email, "song_key": items[0]["song_key"]}
        )
        return respond(200, {"message": "Subscription removed successfully"})

    except ClientError as e:
        return respond(500, {"message": e.response["Error"]["Message"]})


# ──────────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────────

def lambda_handler(event, context):
    http_method = event.get("httpMethod", "")
    path = event.get("path", "")
    query_params = event.get("queryStringParameters") or {}

    # Handle CORS pre-flight from browsers.
    if http_method == "OPTIONS":
        return {"statusCode": 200, "headers": CORS_HEADERS, "body": ""}

    body = None
    raw_body = event.get("body")
    if raw_body:
        try:
            body = json.loads(raw_body)
        except (json.JSONDecodeError, ValueError):
            return respond(400, {"message": "Invalid JSON body"})

    if path == "/login" and http_method == "POST":
        return handle_login(body)

    if path == "/register" and http_method == "POST":
        return handle_register(body)

    if path == "/query" and http_method == "GET":
        return handle_query(query_params)

    if path == "/subscriptions" and http_method == "GET":
        return handle_get_subscriptions(query_params)

    if path == "/subscribe" and http_method == "POST":
        return handle_subscribe(body)

    if path == "/remove" and http_method == "DELETE":
        return handle_remove_subscription(body)

    return respond(404, {"message": "Route not found"})
