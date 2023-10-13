from datetime import datetime
from typing import Optional
import exif
from PIL import Image, UnidentifiedImageError
from utils.file import check_directories
from utils.gps import gps_to_decimal


async def parse_exif_info(path: str, filename: str) -> dict:
    with open(f"{path}/{filename}", "rb") as f:
        img = exif.Image(f)
        if not img.has_exif:
            return {}

        exif_info = img.get_all()

        for datetime_field in ("datetime", "datetime_original", "datetime_digitized"):
            if exif_info.get(datetime_field):
                exif_info[datetime_field] = datetime.strptime(exif_info[datetime_field], "%Y:%m:%d %H:%M:%S")

        if exif_info.get("gps_latitude"):
            exif_info["gps_latitude"] = gps_to_decimal(exif_info["gps_latitude"])

        if exif_info.get("gps_longitude"):
            exif_info["gps_longitude"] = gps_to_decimal(exif_info["gps_longitude"])

        return exif_info


async def resize_image(
        path: str, filename: str, new_width: int, quality: int = 90,
        dest_path: Optional[str] = None,
        dest_filename: Optional[str] = None
):
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
    except UnidentifiedImageError:
        pass


async def rotate_image(
        path: str,
        filename: str,
        angle: int,
        dest_path: Optional[str] = None,
        dest_filename: Optional[str] = None
):
    if not dest_path:
        dest_path = path

    if not dest_filename:
        dest_filename = filename

    img = Image.open(f"{path}/{filename}")
    img = img.rotate(angle, Image.LANCZOS, expand=True)
    check_directories(dest_path)
    img.save(f"{dest_path}/{dest_filename}", 'JPEG', quality=100)
