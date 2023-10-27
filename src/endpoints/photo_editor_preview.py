import os.path
from sqlalchemy import select
from starlette.responses import StreamingResponse
from database import models
from database.transaction import get_session
from endpoints.base import AuthEndpoint
from paths import get_photo_basepath
from utils.image import PhotoEditor


class PhotoEditorEndpoint(AuthEndpoint):
    async def show_preview(self, photo_id: int, **kwargs):
        async with get_session() as db:
            photo = (await db.scalars(
                select(models.Photo)
                .filter(models.Photo.id == photo_id)
            )).one()

            basepath = get_photo_basepath(photo.flight_id)
            filename = photo.filename

        original_filename = '_original_'+filename
        if os.path.exists(f"{basepath}/{original_filename}"):
            filename = original_filename

        editor = PhotoEditor(basepath, filename)
        editor.resize(new_height=900)
        # TODO: idealni je udelat co nejdriv resize
        # velikost muze ovlivnit: orez, otoceni, coz jsou dve nejnarocnejsi operace...
        # ^^ tohle by bylo fajn cachovat

        if kwargs.get("rotate"):
            editor.rotate(kwargs['rotate'], True)

        crop = {
            key.replace("crop_", ""): value
            for key, value in kwargs.items()
            if key in ('crop_left', 'crop_top', 'crop_width', 'crop_height') and value is not None
        }
        if crop and len(crop.keys()) == 4:
            editor.crop(**crop)

        adjustments = {
            key: value for key, value in kwargs.items()
            if key in ('saturation', 'brightness', 'contrast', 'sharpness') and value is not None
        }
        if adjustments:
            editor.adjust(**adjustments)



        return StreamingResponse(content=editor.get_as_stream(), media_type="image/jpeg")

