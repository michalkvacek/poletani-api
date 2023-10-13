from utils.image import resize_image


async def resize_photo(path: str, filename: str):
    return await resize_image(path, filename, new_width=2500, quality=85)


async def generate_thumbnail(path: str, filename: str, quality: int = 90):
    return await resize_image(
        path, filename,
        new_width=300,
        dest_path=f"{path}/thumbs/",
        dest_filename=filename,
        quality=quality
    )
