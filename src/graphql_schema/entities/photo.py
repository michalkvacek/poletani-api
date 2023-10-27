import asyncio
import os
import shutil
from typing import List, Optional
import strawberry
from PIL import Image
from sqlalchemy import delete, select

from background_jobs.elevation import add_terrain_elevation_to_photo
from background_jobs.photo import generate_thumbnail, resize_photo
from database import models
from decorators.endpoints import authenticated_user_only
from database.transaction import get_session
from graphql_schema.entities.resolvers.base import BaseQueryResolver, BaseMutationResolver
from graphql_schema.entities.resolvers.photo import PhotoMutationResolver
from graphql_schema.entities.types.types import Photo, PhotoAdjustment
from logger import log
from paths import get_photo_basepath
from utils.file import delete_file
from utils.image import parse_exif_info, rotate_image_no_crop, adjust_image, resize_image, PhotoEditor
from utils.upload import handle_file_upload
from graphql_schema.entities.types.mutation_input import EditPhotoInput, UploadPhotoInput, AdjustmentInput


@strawberry.type
class PhotoQueries:
    @strawberry.field()
    async def photos(root, info) -> List[Photo]:
        return await BaseQueryResolver(Photo, models.Photo).get_list(user_id=info.context.user_id)

    @strawberry.field()
    async def photo(root, info, id: int) -> Photo:
        return await BaseQueryResolver(Photo, models.Photo).get_one(id, user_id=info.context.user_id)


@strawberry.type
class PhotoMutation:
    @strawberry.mutation
    @authenticated_user_only()
    async def upload_photo(self, info, input: UploadPhotoInput) -> Photo:
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

    @strawberry.mutation()
    @authenticated_user_only()
    async def edit_photo(self, info, id: int, input: EditPhotoInput) -> Photo:
        return await PhotoMutationResolver().update(id, input, info.context.user_id)

    @strawberry.mutation()
    @authenticated_user_only()
    async def change_orientation(self, info, id: int, direction: str) -> Photo:
        async with get_session() as db:
            photo = (await db.scalars(
                BaseQueryResolver(Photo, models.Photo).get_query(user_id=info.context.user_id, object_id=id)
            )).one()
            flight_id = photo.flight_id
            photo_id = photo.id
            photo_filename = photo.filename

        photo_path = get_photo_basepath(flight_id)
        original_filename = "_original_" + photo_filename
        if not os.path.isfile(photo_path + "/" + original_filename):
            shutil.copyfile(photo_path + "/" + photo_filename, photo_path + "/" + original_filename)

        degrees_map = {
            "clockwise": -90,
            "counterClockwise": 90
        }

        # rotate original
        editor = PhotoEditor(photo_path, original_filename)
        editor.rotate(degrees=degrees_map[direction], crop_after_rotate=False)
        editor.write_to_file(quality=100)

        # rotate possibly adjusted image
        editor = PhotoEditor(photo_path, photo_filename)
        editor.rotate(degrees=degrees_map[direction], crop_after_rotate=False)
        editor.write_to_file(quality=100)

        info.context.background_tasks.add_task(generate_thumbnail, path=photo_path, filename=photo_filename)

        async with get_session() as db:
            photo = await models.Photo.update(db, {
                "width": editor.img.width,
                "height": editor.img.height
            }, id=photo_id)
            return Photo(**photo.as_dict())

    @strawberry.mutation()
    @authenticated_user_only()
    async def adjust_photo(self, info, id: int, adjustment: AdjustmentInput) -> Photo:
        async with get_session() as db:
            photo = (await db.scalars(
                BaseQueryResolver(Photo, models.Photo).get_query(user_id=info.context.user_id, object_id=id)
            )).one()
            flight_id = photo.flight_id
            photo_filename = photo.filename
            photo_as_dict = photo.as_dict()

        photo_path = get_photo_basepath(flight_id)

        # TOOD: presunout do samostatne metody
        original_filename = "_original_" + photo_filename
        if not os.path.isfile(photo_path + "/" + original_filename):
            shutil.copyfile(photo_path + "/" + photo_filename, photo_path + "/" + original_filename)

        editor = (
            PhotoEditor(photo_path, original_filename)
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

        editor.write_to_file(dest_filename=photo_filename)

        info.context.background_tasks.add_task(generate_thumbnail, path=photo_path, filename=photo_filename)

        async with get_session() as db:
            await db.execute(delete(models.PhotoAdjustment).filter(models.PhotoAdjustment.photo_id == id))

            crop_info = {"crop_" + key: value for key, value in adjustment.crop.to_dict().items()} if adjustment.crop else {}
            await models.PhotoAdjustment.create(db, {
                "photo_id": id,
                "contrast": adjustment.contrast,
                "saturation": adjustment.saturation,
                "brightness": adjustment.brightness,
                "rotate": adjustment.rotate,
                "sharpness": adjustment.sharpness,
                **crop_info
            })

            width, height = editor.img_size
            await models.Photo.update(db, {"width": width, "height": height}, id=id)

        return Photo(**photo_as_dict)

    @strawberry.mutation()
    @authenticated_user_only()
    async def delete_photo(self, info, id: int) -> Photo:
        photo = await PhotoMutationResolver().delete(user_id=info.context.user_id, id=id)

        base_path = get_photo_basepath(photo.flight_id)
        delete_file(f"{base_path}/{photo.filename}", silent=True)
        delete_file(f"{base_path}/thumbs/{photo.filename}", silent=True)

        return photo
