import asyncio
import sys
from PIL import Image
from PIL.Image import DecompressionBombWarning
from sqlalchemy import select

sys.path.insert(0, "/app/src")
from paths import get_photo_basepath  # noqa
from database import async_session, models  # noqa


async def add_sizes_to_photos():
    async with async_session() as session:
        photos = (await session.scalars(
            select(models.Photo)
        )).all()

        for photo in photos:
            path = get_photo_basepath(photo.flight_id)

            try:
                img = Image.open(f"{path}/{photo.filename}")
                await models.Photo.update(session, {"width": img.width, "height": img.height}, obj=photo)
                print(path, photo.filename, img.width, img.height, "OK")
            except (Exception, DecompressionBombWarning) as e:
                print(path, photo.filename, e)

        await session.flush()
        await session.commit()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(add_sizes_to_photos())
