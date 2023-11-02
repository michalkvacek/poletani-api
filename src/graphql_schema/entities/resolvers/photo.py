import os
import shutil
from PIL import Image
from pydantic import BaseModel
from sqlalchemy import update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from background_jobs.elevation import add_terrain_elevation_to_photo
from background_jobs.photo import generate_thumbnail, resize_photo
from database import models
from database.transaction import get_session
from graphql_schema.entities.helpers.combobox import handle_combobox_save
from graphql_schema.entities.resolvers.base import BaseMutationResolver
from graphql_schema.entities.types.mutation_input import EditPhotoInput, UploadPhotoInput, AdjustmentInput
from graphql_schema.entities.types.types import Photo
from paths import get_photo_basepath
from utils.file import delete_file
from utils.image import PhotoEditor, parse_exif_info
from utils.upload import handle_file_upload


class PhotoDetailInfo(BaseModel):
    filename: str
    original_filename: str
    path: str
    flight_id: int


class PhotoMutationResolver(BaseMutationResolver):
    def __init__(self):
        super().__init__(Photo, models.Photo)

    @staticmethod
    async def _reset_flight_cover(db: AsyncSession, flight_id: int, ignored_photo_id: int):
        (await db.execute(
            update(models.Photo)
            .filter(models.Photo.flight_id == flight_id)
            .filter(models.Photo.id != ignored_photo_id)
            .values(is_flight_cover=False))
         )

    @staticmethod
    def _copy_original(path: str, filename: str):
        original_filename = "_original_" + filename
        if not os.path.isfile(path + "/" + original_filename):
            shutil.copyfile(path + "/" + filename, path + "/" + original_filename)

        return original_filename

    async def _get_photo_details(self, id: int, user_id: int):
        async with get_session() as db:
            photo = await self._get_one(db, id, created_by_id=user_id)
            flight_id = photo.flight_id
            filename = photo.filename

        path = get_photo_basepath(flight_id)
        return PhotoDetailInfo(
            flight_id=flight_id,
            path=path,
            filename=filename,
            original_filename=self._copy_original(path, filename)
        )

    async def upload(self, info, input: UploadPhotoInput) -> Photo:
        path = get_photo_basepath(input.flight_id)
        filename = await handle_file_upload(input.photo, path)
        exif_info = await parse_exif_info(path, filename)

        img = Image.open(f"{path}/{filename}")
        photo = await PhotoMutationResolver().create(
            user_id=info.context.user_id,
            data={
                "flight_id": input.flight_id,
                "name": input.name,
                "filename": filename,
                "width": img.width,
                "height": img.height,
                "description": input.description,
                "exposed_at": exif_info.get("datetime_original"),
                "gps_latitude": exif_info.get("gps_latitude"),
                "gps_longitude": exif_info.get("gps_longitude"),
                "gps_altitude": exif_info.get("gps_altitude"),
                "is_flight_cover": False,
            },
        )

        info.context.background_tasks.add_task(resize_photo, path=path, filename=filename, photo_id=photo.id)
        info.context.background_tasks.add_task(generate_thumbnail, path=path, filename=filename)

        if exif_info.get("gps_latitude") and exif_info.get("gps_longitude"):
            info.context.background_tasks.add_task(add_terrain_elevation_to_photo, photo=photo)

        return photo

    async def update(self, id: int, input: EditPhotoInput, user_id: int) -> Photo:
        data = input.to_dict()

        async with get_session() as db:
            photo = await self._get_one(db, id, created_by_id=user_id)
            if input.point_of_interest:
                data['point_of_interest_id'] = await handle_combobox_save(
                    db,
                    models.PointOfInterest,
                    input.point_of_interest,
                    user_id,
                    extra_data={"description": ""}
                )

            if input.is_flight_cover:
                # reset other covers
                await self._reset_flight_cover(db, photo.flight_id, id)

            return await self._do_update(db, obj=photo, data=data)

    async def change_orientation(self, id: int, user_id: int, direction: str, info):
        photo = await self._get_photo_details(id, user_id)

        degrees_map = {
            "clockwise": -90,
            "counterClockwise": 90
        }

        # rotate original
        editor = PhotoEditor(photo.path, photo.original_filename)
        editor.rotate(degrees=degrees_map[direction], crop_after_rotate=False)
        editor.write_to_file(quality=100)

        # rotate possibly adjusted image
        editor = PhotoEditor(photo.path, photo.filename)
        editor.rotate(degrees=degrees_map[direction], crop_after_rotate=False)
        editor.write_to_file(quality=100)

        info.context.background_tasks.add_task(generate_thumbnail, path=photo.path, filename=photo.filename)

        async with get_session() as db:
            return await self._do_update(db, obj={"id": id}, data={
                "width": editor.img.width,
                "height": editor.img.height
            })

    async def adjust(self, id: int, user_id: int, adjustment: AdjustmentInput, info):
        photo = await self._get_photo_details(id, user_id)
        editor = (
            PhotoEditor(photo.path, photo.original_filename)
            .adjust(
                brightness=adjustment.brightness,
                contrast=adjustment.contrast,
                sharpness=adjustment.sharpness,
                saturation=adjustment.saturation
            )
        )

        if adjustment.rotate:
            rotate_angle = adjustment.rotate
            editor.rotate(rotate_angle, adjustment.crop_after_rotate)

        if adjustment.crop:
            editor.crop(**adjustment.crop.to_dict())

        editor.write_to_file(dest_filename=photo.filename)

        info.context.background_tasks.add_task(generate_thumbnail, path=photo.path, filename=photo.filename)

        async with (get_session() as db):
            await db.execute(delete(models.PhotoAdjustment).filter(models.PhotoAdjustment.photo_id == id))

            crop_info = {
                "crop_" + key: value
                for key, value in adjustment.crop.to_dict().items()
            } if adjustment.crop else {}
            await models.PhotoAdjustment.create(db, {
                "photo_id": id,
                "contrast": adjustment.contrast,
                "saturation": adjustment.saturation,
                "brightness": adjustment.brightness,
                "rotate": adjustment.rotate,
                "sharpness": adjustment.sharpness,
                **crop_info
            })

            return await self._do_update(db, obj={"id": id}, data={
                "width": editor.img.width,
                "height": editor.img.height
            })

    async def delete(self, user_id: int, id: int) -> Photo:
        photo = await super().delete(user_id, id)

        base_path = get_photo_basepath(photo.flight_id)
        delete_file(f"{base_path}/{photo.filename}", silent=True)
        delete_file(f"{base_path}/_original_{photo.filename}", silent=True)
        delete_file(f"{base_path}/thumbs/{photo.filename}", silent=True)

        return photo
