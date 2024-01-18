import os
import shutil
from time import time
from typing import Optional
from PIL import Image
from pydantic import BaseModel
from sqlalchemy import delete, insert
from background_jobs.elevation import add_terrain_elevation_to_photo
from background_jobs.photo import generate_thumbnail, resize_photo
from database import models
from database.transaction import get_session
from graphql_schema.entities.helpers.combobox import handle_combobox_save
from graphql_schema.entities.resolvers.base import BaseMutationResolver, BaseQueryResolver
from graphql_schema.entities.types.mutation_input import EditPhotoInput, UploadPhotoInput, AdjustmentInput
from graphql_schema.entities.types.types import Photo
from paths import get_photo_basepath
from utils.file import delete_file
from utils.image import PhotoEditor, parse_exif_info
from utils.upload import handle_file_upload


class PhotoQueryResolver(BaseQueryResolver):

    def __init__(self):
        super().__init__(Photo, models.Photo)

    def get_query(
            self,
            user_id: Optional[int] = None,
            object_id: Optional[int] = None,
            order_by: Optional[list] = None,
            only_public: Optional[bool] = False,
            *args, **kwargs
    ):

        query = super().get_query(
            user_id, object_id, order_by,
            **{
                field: kwargs[field]
                for field in ("aircraft_id", "point_of_interest_id", "flight_id")
                if kwargs.get(field)
            }
        )

        if kwargs.get("public"):
            query = (
                query.join(models.Flight, onclause=models.Photo.flight_id == models.Flight.id)
                .filter(models.Flight.is_public.is_(True))
            )

        if kwargs.get("copilot_id"):
            query = (
                query.join(models.copilot_has_photo)
                .filter(models.copilot_has_photo.c.copilot_id == kwargs['copilot_id'])
            )

        return query


class PhotoDetailInfo(BaseModel):
    filename: str
    original_filename: str
    path: str
    flight_id: int


class PhotoMutationResolver(BaseMutationResolver):
    def __init__(self):
        super().__init__(Photo, models.Photo)

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
            filename = photo.filename+"."+photo.filename_extension

        path = get_photo_basepath(flight_id)
        return PhotoDetailInfo(
            flight_id=flight_id,
            path=path,
            filename=filename,
            original_filename=self._copy_original(path, filename)
        )

    async def upload(self, info, input: UploadPhotoInput) -> Photo:
        path = get_photo_basepath(input.flight_id)
        img_name = await handle_file_upload(input.photo, path, uid_prefix=False, overwrite=False)

        exif_info = await parse_exif_info(path, img_name)

        img = Image.open(f"{path}/{img_name}")
        filename, filename_ext = os.path.splitext(img_name)

        async with get_session() as db:
            photo = await PhotoMutationResolver()._do_create(
                db,
                data={
                    "flight_id": input.flight_id,
                    "name": input.name,
                    "filename": filename,
                    "filename_extension": filename_ext[1:],  # nechci ukladat tecku na zacatku
                    "cache_key": int(time()),
                    "width": img.width,
                    "height": img.height,
                    "description": input.description,
                    "exposed_at": exif_info.get("datetime_original"),
                    "gps_latitude": exif_info.get("gps_latitude"),
                    "gps_longitude": exif_info.get("gps_longitude"),
                    "gps_altitude": exif_info.get("gps_altitude"),
                    "created_by_id": info.context.user_id,
                },
            )

        info.context.background_tasks.add_task(resize_photo, path=path, filename=img_name, photo_id=photo.id)
        info.context.background_tasks.add_task(generate_thumbnail, path=path, filename=img_name)

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

            if input.copilots is not None:
                await db.execute(delete(models.copilot_has_photo).filter_by(photo_id=id))
                for copilot in input.copilots:
                    await db.execute(insert(models.copilot_has_photo).values(photo_id=id, copilot_id=copilot.id))

            return await self._do_update(db, obj=photo, data=data)

    async def change_orientation(self, id: int, user_id: int, direction: str, info):
        photo = await self._get_photo_details(id, user_id)

        degrees_map = {
            "clockwise": 90,
            "counterClockwise": -90
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
                "height": editor.img.height,
                "cache_key": int(time())
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
                "height": editor.img.height,
                "cache_key": int(time())
            })

    async def delete(self, user_id: int, id: int) -> Photo:
        photo = await super().delete(user_id, id)

        base_path = get_photo_basepath(photo.flight_id)

        files_to_delete = [
            photo.filename,
            f"_original_{photo.filename}",
            f"{photo.filename}.{photo.filename_extension}",
            f"_original_{photo.filename}.{photo.filename_extension}",
            f"thumbs/{photo.filename}",
            f"thumbs/{photo.filename}.{photo.filename_extension}",
            f"thumbs/{photo.filename}.webp",
        ]
        for filename in files_to_delete:
            delete_file(f"{base_path}/{filename}", silent=True)

        return photo
