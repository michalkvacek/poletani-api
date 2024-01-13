import os
from typing import Optional
from config import API_URL
from logger import log

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
    filename = root.filename if not root.filename_extension else f"{root.filename}.{root.filename_extension}"
    return get_public_url(f"photos/{root.flight_id}/{filename}?cache={root.cache_key}")


def get_photo_thumbnail_url(root) -> str:
    filename = root.filename if not root.filename_extension else f"{root.filename}.{root.filename_extension}"
    thumbnail_names = [
        f"thumbs/{root.filename}.webp",
        f"thumbs/{filename}",
        filename,
    ]

    for thumbnail in thumbnail_names:
        if os.path.isfile(f"{get_photo_basepath(root.flight_id)}/{thumbnail}"):
            # TODO: logovani
            return get_public_url(f"photos/{root.flight_id}/{thumbnail}?cache={root.cache_key}")
        else:
            log.warning(f"Missing thumbnail {thumbnail} in flight ID={root.flight_id}")

    # TODO: doplnit chybejici nahled, tohle by se ale nikdy nemelo stat! Vzdy musi existovat alespon originalni fotka
    return get_public_url(f"photos/missing-thumbnail.webp")


def get_avatar_url(user) -> str:
    return get_public_url(f"profile/{user.id}/{user.avatar_image_filename}") if user.avatar_image_filename else None


def get_title_image_url(user):
    if not user.title_image_filename:
        return f"{API_URL}/static/default-title-image.jpg"

    return get_public_url(f"profile/{user.id}/{user.title_image_filename}")
