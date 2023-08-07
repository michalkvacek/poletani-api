import os
import uuid
from datetime import datetime
from typing import Optional, Tuple
import exif
from PIL import Image, UnidentifiedImageError
from strawberry.file_uploads import Upload


def get_public_url(filename: Optional[str]):
    # TODO: pouzit staticfiles z /uploads - port na API, nginx nebude potreba (pro dev)
    return f"http://localhost:8999/{filename}" if filename else None


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


async def generate_thumbnail(path: str, filename: str, size: Tuple[int, int]):
    try:
        image = Image.open(f"{path}/{filename}")
        image.thumbnail(size)
        check_directories(f"{path}/thumbs/")
        image.save(f"{path}/thumbs/{filename}")
    except UnidentifiedImageError:
        pass


def delete_file(path: str, silent: bool = False):
    os.remove(path)
