import asyncio
import os.path
import time

import sys
from PIL import Image
from PIL.Image import DecompressionBombWarning
from sqlalchemy import select

sys.path.insert(0, "/app/src")
from paths import get_photo_basepath  # noqa
from database import async_session, models  # noqa


async def migrate_photos_to_webp():
    async with async_session() as session:
        photos = (await session.scalars(
            select(models.Photo).filter(models.Photo.filename_extension == "")
        )).all()

        for photo in photos:
            path = get_photo_basepath(photo.flight_id)

            try:
                img = Image.open(f"{path}/{photo.filename}")

                filename, ext = os.path.splitext(photo.filename)
                new_filename = filename[37:]  # vyhodim uuid z filename

                img.save(f"{path}/{new_filename}.webp", format="webp")

                thumb = Image.open(f"{path}/thumbs/{photo.filename}")
                thumb.save(f"{path}/thumbs/{new_filename}.webp", format="webp")

                await models.Photo.update(session, {
                    "filename": new_filename,
                    "cache_key": int(time.time()),
                    "filename_extension": "webp",
                }, obj=photo)
                print(path, photo.filename, "=>", new_filename, "OK")
            except (Exception, DecompressionBombWarning) as e:
                print(path, photo.filename, e)

        await session.flush()
        await session.commit()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(migrate_photos_to_webp())
