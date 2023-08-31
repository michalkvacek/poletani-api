import os
import uuid
from datetime import datetime
from typing import Optional, Tuple
import exif
from PIL import Image, UnidentifiedImageError
from strawberry.file_uploads import Upload

from config import API_URL


def get_public_url(filename: Optional[str]):
    return f"{API_URL}/uploads/{filename}" if filename else None


def check_directories(path: str):
    if not os.path.isdir(path):
        os.makedirs(path)


def file_exists(path: str):
    return os.path.isfile(path)


async def handle_file_upload(file: Upload, path: str):
    check_directories(path)

    filename = f"{uuid.uuid4()}-{file.filename}"

    content = await file.read()
    image = open(path + "/" + filename, "wb")
    image.write(content)
    image.close()

    return filename


def gps_to_decimal(input: Tuple[float, float, float]) -> float:
    d, m, s = input
    return d + (m / 60.0) + (s / 3600.0)


async def parse_exif_info(path: str, filename: str) -> dict:
    with open(f"{path}/{filename}", "rb") as f:
        img = exif.Image(f)
        if not img.has_exif:
            return {}

        exif_info = img.get_all()

        for datetime_field in ("datetime", "datetime_original", "datetime_digitized"):
            if exif_info.get(datetime_field):
                print(exif_info[datetime_field])
                exif_info[datetime_field] = datetime.strptime(exif_info[datetime_field], "%Y:%m:%d %H:%M:%S")

        if exif_info.get("gps_latitude"):
            exif_info["gps_latitude"] = gps_to_decimal(exif_info["gps_latitude"])

        if exif_info.get("gps_longitude"):
            exif_info["gps_longitude"] = gps_to_decimal(exif_info["gps_longitude"])

        return exif_info


async def resize_image(path: str, filename: str, new_width: int, quality: int = 90, dest_path: str = None, dest_filename: str = None):
    if not dest_path:
        dest_path = path

    if not dest_filename:
        dest_filename = filename

    try:
        image = Image.open(f"{path}/{filename}")

        width, height = image.size
        new_height = int(new_width * height / width)

        image = image.resize((new_width, new_height), Image.LANCZOS)
        check_directories(dest_path)
        image.save(f"{dest_path}/{dest_filename}", 'JPEG', quality=quality)
    except UnidentifiedImageError as e:
        pass


async def generate_thumbnail(path: str, filename: str, quality: int = 90):
    return await resize_image(
        path, filename,
        new_width=300,
        dest_path=f"{path}/thumbs/",
        dest_filename=filename,
        quality=quality
    )


def delete_file(path: str, silent: bool = False):
    try:
        os.remove(path)
    except Exception:
        if not silent:
            raise
