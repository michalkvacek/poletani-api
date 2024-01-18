import os.path
from time import time
from database import models
from database.transaction import get_session
from utils.image import PhotoEditor


async def resize_photo(path: str, filename: str, photo_id: int):
    editor = PhotoEditor(path, filename)
    editor.resize(new_width=2500)

    name, _ = os.path.splitext(filename)
    editor.write_to_file(quality=95, format_="webp", dest_filename=f"{name}.webp")
    editor.write_to_file(quality=80)  # toto je potreba pro prvni nacteni nahledu ihned po nahrani, pripadne pro
    # vygenerovani nahledu (async, muze se delat pred/behem zmensovani fotky -> v tu dobu jeste neexistuje webp)
    width, height = editor.img_size

    # TODO: doresit uklid JPGu -> jsou zbytecne

    async with get_session() as db:
        await models.Photo.update(
            db,
            id=photo_id,
            data={
                "width": width,
                "height": height,
                "filename_extension": "webp",
                "cache_key": int(time())
            })


async def generate_thumbnail(path: str, filename: str):
    editor = PhotoEditor(path, filename)
    editor.resize(new_width=300)

    name, _ = os.path.splitext(filename)
    editor.write_to_file(
        quality=85,
        dest_path=f"{path}/thumbs",
        dest_filename=f"{name}.webp",
        format_="webp")
