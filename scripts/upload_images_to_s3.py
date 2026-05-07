import json
import os
import re
import requests
import boto3
from botocore.exceptions import ClientError

REGION = "us-east-1"
#BUCKET_NAME = "a2-s3music"
BUCKET_NAME = "a2-s3music-v2"
JSON_FILE = "2026a2_songs.json"
DOWNLOAD_FOLDER = "downloaded_images"


def load_songs(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    if isinstance(data, dict) and "songs" in data and isinstance(data["songs"], list):
        return data["songs"]

    raise ValueError("JSON format invalid: 'songs' key not found or is not a list.")


# def safe_file_name(text):
#     text = text.strip()
#     text = re.sub(r"[<>:\"/\\\\|?*]", "", text)
#     text = re.sub(r"\s+", "_", text)
#     return text


def get_file_extension_from_url(url):
    lower_url = url.lower()
    if lower_url.endswith(".png"):
        return ".png"
    if lower_url.endswith(".jpeg"):
        return ".jpeg"
    if lower_url.endswith(".jpg"):
        return ".jpg"
    if lower_url.endswith(".webp"):
        return ".webp"
    return ".jpg"


def download_image(url, local_path):
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    with open(local_path, "wb") as file:
        file.write(response.content)


def upload_file_to_s3(local_path, bucket_name, s3_key, s3_client):
    s3_client.upload_file(
        local_path,
        bucket_name,
        s3_key,
        ExtraArgs={"ContentType": get_content_type(local_path)}
    )


def get_content_type(file_path):
    lower_path = file_path.lower()
    if lower_path.endswith(".png"):
        return "image/png"
    if lower_path.endswith(".jpeg") or lower_path.endswith(".jpg"):
        return "image/jpeg"
    if lower_path.endswith(".webp"):
        return "image/webp"
    return "application/octet-stream"


def main():
    os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

    songs = load_songs(JSON_FILE)
    s3_client = boto3.client("s3", region_name=REGION)

    processed_artists = set()
    uploaded_count = 0
    skipped_count = 0
    failed_count = 0

    for song in songs:
        try:
            artist = song["artist"].strip()
            image_url = song["img_url"].strip()

            if artist in processed_artists:
                skipped_count += 1
                print(f"Skipped duplicate artist image: {artist}")
                continue

            #file_extension = get_file_extension_from_url(image_url)
            #safe_artist = safe_file_name(artist)

            safe_artist = image_url.split("/")[-1]

            #local_file_name = f"{safe_artist}{file_extension}"
            local_file_name = f"{safe_artist}"
            local_file_path = os.path.join(DOWNLOAD_FOLDER, local_file_name)

            s3_key = f"artist-images/{local_file_name}"

            print(f"Downloading image for: {artist}")
            download_image(image_url, local_file_path)

            print(f"Uploading to S3: {s3_key}")
            upload_file_to_s3(local_file_path, BUCKET_NAME, s3_key, s3_client)

            processed_artists.add(artist)
            uploaded_count += 1
            print(f"Uploaded successfully: {artist}")

        except KeyError as e:
            failed_count += 1
            print(f"Missing required field: {e}")

        except requests.RequestException as e:
            failed_count += 1
            print(f"Download failed for artist '{song.get('artist', 'UNKNOWN')}': {e}")

        except ClientError as e:
            failed_count += 1
            print(f"S3 upload failed for artist '{song.get('artist', 'UNKNOWN')}': {e.response['Error']['Message']}")

        except Exception as e:
            failed_count += 1
            print(f"Unexpected error for artist '{song.get('artist', 'UNKNOWN')}': {e}")

    print()
    print("Finished image download and upload process.")
    print(f"Uploaded: {uploaded_count}")
    print(f"Skipped duplicates: {skipped_count}")
    print(f"Failed: {failed_count}")


if __name__ == "__main__":
    main()