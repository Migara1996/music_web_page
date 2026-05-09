import json
import os
import re
import requests
import boto3
from botocore.exceptions import ClientError

REGION = "us-east-1" # AWS region 
BUCKET_NAME = "a2-s3music" # Bucket Name
JSON_FILE = "2026a2_songs.json" # music file
DOWNLOAD_FOLDER = "downloaded_images" # Folder that saves downloaded images


def load_songs(file_path):
    """
    Parses the JSON file to retrieve the list of song objects.
    Includes validation to ensure the 'songs' key exists and is iterable.
    
    Source: Python json module documentation 
    (https://docs.python.org/3/library/json.html)
    """
    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    if isinstance(data, dict) and "songs" in data and isinstance(data["songs"], list):
        return data["songs"]

    raise ValueError("JSON format invalid: 'songs' key not found or is not a list.")

# Extract file extensions of images
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

# Download image by using given image_url in json file
def download_image(url, local_path):
    """
    Streams binary content from the web and saves it to a local file.
    
    Source: Requests Library - Binary Response Content 
    (https://requests.readthedocs.io/en/latest/user/quickstart/#binary-response-content)
    """
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    with open(local_path, "wb") as file:
        file.write(response.content)

# Upload downloaded images to S3 bucket
def upload_file_to_s3(local_path, bucket_name, s3_key, s3_client):
     """
    Uploads the local image file to the destination S3 bucket.
    Includes the ContentType extra argument to ensure correct browser rendering.
    
    Source: Boto3 S3 Client upload_file documentation 
    (https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3/client/upload_file.html)
    """
    s3_client.upload_file(
        local_path,
        bucket_name,
        s3_key,
        ExtraArgs={"ContentType": get_content_type(local_path)}
    )

# 
def get_content_type(file_path):
    """
    Helper function to map file extensions to MIME types for S3 metadata.
    """
    lower_path = file_path.lower()
    if lower_path.endswith(".png"):
        return "image/png"
    if lower_path.endswith(".jpeg") or lower_path.endswith(".jpg"):
        return "image/jpeg"
    if lower_path.endswith(".webp"):
        return "image/webp"
    return "application/octet-stream"

# Main function that operates download and upload 
def main():
    """
    Orchestrates the image processing pipeline:
    1. Reads music data.
    2. Downloads unique artist images.
    3. Uploads files to S3 with sanitized naming.
    """
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
            
            safe_artist = image_url.split("/")[-1]

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