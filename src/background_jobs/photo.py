from database import models
from database.transaction import get_session
from utils.image import PhotoEditor


async def resize_photo(path: str, filename: str, photo_id: int):
    editor = PhotoEditor(path, filename)
    editor.resize(new_width=2500)
    editor.write_to_file(quality=85)
    width, height = editor.img_size

    async with get_session() as db:
        await models.Photo.update(db, {"width": width, "height": height}, id=photo_id)


async def generate_thumbnail(path: str, filename: str):
    editor = PhotoEditor(path, filename)
    editor.resize(new_width=300)
    editor.write_to_file(quality=85, dest_path=f"{path}/thumbs")
