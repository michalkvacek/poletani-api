import io

import math
from datetime import datetime
from typing import Optional, Tuple
import exif
from PIL import Image, UnidentifiedImageError
from PIL.ImageEnhance import Brightness, Contrast, Color, Sharpness
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


class PhotoEditor:
    def __init__(self, path: str, filename: str):
        self.path = path
        self.filename = filename

        self.img = Image.open(f"{path}/{filename}")
        self.img_size = self.img.size

    def resize(self, new_width: Optional[int] = None, new_height: Optional[int] = None):
        if not new_width and not new_height:
            raise ValueError("Set either new_width or new_height")

        w, h = self.img.size
        aspect_ratio = w / h

        if not new_width:
            # TODO: tohle bude asi blbe, tu se bude muset asi delit?
            new_width = int(new_height * aspect_ratio)

        if not new_height:
            new_height = int(new_width / aspect_ratio)

        self.img = self.img.resize((new_width, new_height), Image.BICUBIC)
        self.img_size = self.img.size

        return self

    def _get_cropbox_after_rotate(self, degrees: float, rotated_width: int, rotated_height: int) -> Tuple[int, int]:
        original_width, original_height = self.img_size
        aspect_ratio = float(original_width) / original_height
        rotated_aspect_ratio = float(rotated_width) / rotated_height
        angle = math.fabs(degrees) * math.pi / 180

        if aspect_ratio < 1:
            total_height = float(original_width) / rotated_aspect_ratio
        else:
            total_height = float(original_height)

        h = total_height / (aspect_ratio * math.sin(angle) + math.cos(angle))
        w = h * aspect_ratio

        return round(w), round(h)

    def rotate(self, degrees: float, crop_after_rotate: bool = False):
        degrees *= -1
        self.img = self.img.rotate(degrees, resample=Image.Resampling.BICUBIC, expand=True)

        if crop_after_rotate:
            rotated_width, rotated_height = self.img.size
            new_width, new_height = self._get_cropbox_after_rotate(degrees, rotated_width, rotated_height)

            left = round((rotated_width - new_width) / 2)
            top = round((rotated_height - new_height) / 2)

            self.img = self.img.crop((left, top, new_width, new_height))

        self.img_size = self.img.size
        return self

    def crop(self, left: float, top: float, width: float, height: float):
        w, h = self.img_size
        left_px = int(left * w)
        top_px = int(top * h)
        width_px = int(width * w)
        height_px = int(height * h)

        self.img = self.img.crop((left_px, top_px, left_px + width_px, top_px + height_px))
        self.img_size = self.img.size
        return self

    def adjust(
            self,
            brightness: Optional[float] = None,
            contrast: Optional[float] = None,
            saturation: Optional[float] = None,
            sharpness: Optional[float] = None
    ):
        adjustments = [
            (Brightness, brightness),
            (Contrast, contrast),
            (Color, saturation),
            (Sharpness, sharpness)
        ]
        for adjustment, value in adjustments:
            if value is not None:
                self.img = adjustment(self.img).enhance(value)

        return self

    def get_as_stream(self):
        img_io = io.BytesIO()
        self.img.save(img_io, 'JPEG')
        img_io.seek(0)

        return img_io

    def write_to_file(
            self, quality: int = 90, dest_path: Optional[str] = None, dest_filename: Optional[str] = None
    ) -> str:
        dest = f"{dest_path or self.path}/{dest_filename or self.filename}"
        self.img.save(dest, 'JPEG', quality=quality)

        return dest



# -----------
# odsud niz to bude vse asi na smazani, vse by mela umet trida PhotoEditor

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

        return new_width, new_height
    except UnidentifiedImageError:
        pass


def crop_image_after_rotate(
        original_width: int, original_height: int, rotated_width: int, rotated_height: int, degrees: float
) -> Tuple[int, int]:
    aspect_ratio = float(original_width) / original_height
    rotated_aspect_ratio = float(rotated_width) / rotated_height
    angle = math.fabs(degrees) * math.pi / 180

    if aspect_ratio < 1:
        total_height = float(original_width) / rotated_aspect_ratio
    else:
        total_height = float(original_height)

    h = total_height / (aspect_ratio * math.sin(angle) + math.cos(angle))
    w = h * aspect_ratio

    return round(w), round(h)


async def rotate_image_no_crop(
        path: str,
        filename: str,
        angle: float,
        dest_path: Optional[str] = None,
        dest_filename: Optional[str] = None
):
    if not dest_path:
        dest_path = path

    if not dest_filename:
        dest_filename = filename

    img = Image.open(f"{path}/{filename}")
    rotated_img = img.rotate(angle, Image.BICUBIC, expand=True)

    check_directories(dest_path)
    rotated_img.save(f"{dest_path}/{dest_filename}", 'JPEG', quality=100)


async def adjust_image(
        path: str,
        filename: str,
        rotate: float,
        brightness: float,
        contrast: float,
        saturation: float,
        sharpness: float,
        crop: dict,
        dest_path: Optional[str] = None,
        dest_filename: Optional[str] = None
):
    if not dest_path:
        dest_path = path

    if not dest_filename:
        dest_filename = filename

    img = Image.open(f"{path}/{filename}")

    if rotate:
        rotated_img = img.rotate(rotate, Image.BICUBIC, expand=True)

        width, height = img.size
        rotated_width, rotated_height = rotated_img.size
        new_width, new_height = crop_image_after_rotate(width, height, rotated_width, rotated_height, rotate)

        left = round((rotated_width - new_width) / 2)
        top = round((rotated_height - new_height) / 2)

        img = rotated_img.crop((left, top, left + new_width, top + new_height))

    adjustments = [
        (Brightness, brightness),
        (Contrast, contrast),
        (Color, saturation),
        (Sharpness, sharpness)
    ]
    for adj, value in adjustments:
        img = adj(img).enhance(value)

    if crop:
        w, h = img.size
        left = crop['left'] * w
        top = crop['top'] * h
        width = crop['width'] * w
        height = crop['height'] * h
        img = img.crop((left, top, left + width, top + height))

    img.save(f"{dest_path}/{dest_filename}", 'JPEG', quality=100)
