import os
from typing import Optional
from config import API_URL

PHOTO_BASE_PATH = ""
AIRCRAFT_BASE_PATH = ""
FLIGHT_BASE_PATH = ""
FLIGHT_GPX_TRACK_PATH = "/app/uploads/tracks"
AIRCRAFT_UPLOAD_DEST_PATH = "/app/uploads/aircrafts/"


def get_photo_basepath(flight_id: int) -> str:
    return f"/app/uploads/photos/{flight_id}"


def get_public_url(filename: Optional[str]) -> str:
    return f"{API_URL}/uploads/{filename}" if filename else None


def get_photo_url(root) -> str:
    return get_public_url(f"photos/{root.flight_id}/{root.filename}")


def get_photo_thumbnail_url(root) -> str:
    thumbnail = get_photo_basepath(root.flight_id) + "/thumbs/" + root.filename
    if not os.path.isfile(thumbnail):
        # TODO: logovani
        return get_public_url(f"photos/{root.flight_id}/{root.filename}")

    return get_public_url(f"photos/{root.flight_id}/thumbs/{root.filename}")


def get_avatar_url(user) -> str:
    return get_public_url(f"profile/{user.id}/{user.avatar_image_filename}") if user.avatar_image_filename else None


def get_title_image_url(user):
    if not user.title_image_filename:
        return f"{API_URL}/static/default-title-image.jpg"

    return get_public_url(f"profile/{user.id}/{user.title_image_filename}")
