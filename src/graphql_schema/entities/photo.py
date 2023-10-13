import asyncio
from typing import List, Optional
import strawberry
from sqlalchemy import update
from strawberry.file_uploads import Upload
from background_jobs.elevation import add_terrain_elevation_to_photo
from background_jobs.photo import generate_thumbnail, resize_photo
from database import models
from decorators.endpoints import authenticated_user_only
from database.transaction import get_session
from graphql_schema.entities.resolvers.base import BaseQueryResolver, BaseMutationResolver
from graphql_schema.entities.types.types import Photo
from paths import get_photo_basepath
from graphql_schema.entities.helpers.combobox import handle_combobox_save
from utils.file import delete_file
from utils.image import parse_exif_info, rotate_image
from utils.upload import handle_file_upload
from graphql_schema.entities.types.mutation_input import ComboboxInput


@strawberry.type
class PhotoQueries:
    @strawberry.field()
    async def photos(root, info) -> List[Photo]:
        return await BaseQueryResolver(Photo, models.Photo).get_list(user_id=info.context.user_id)


@strawberry.type
class UploadPhotoMutation:
    @strawberry.input
    class UploadPhotoInput:
        photo: Upload
        flight_id: int
        name: Optional[str] = None
        description: Optional[str] = None
        point_of_interest: Optional[ComboboxInput] = None

    @strawberry.mutation
    @authenticated_user_only()
    async def upload_photo(self, info, input: UploadPhotoInput) -> Photo:
        path = get_photo_basepath(input.flight_id)
        filename = await handle_file_upload(input.photo, path)
        exif_info = await parse_exif_info(path, filename)

        async with get_session() as db:
            photo_model = await models.Photo.create(data={
                "flight_id": input.flight_id,
                "name": input.name,
                "filename": filename,
                "description": input.description,
                "exposed_at": exif_info.get("datetime_original"),
                "gps_latitude": exif_info.get("gps_latitude"),
                "gps_longitude": exif_info.get("gps_longitude"),
                "gps_altitude": exif_info.get("gps_altitude"),
                "is_flight_cover": False,
                "created_by_id": info.context.user_id,
            }, db_session=db)
            photo = Photo(**photo_model.as_dict())

        info.context.background_tasks.add_task(resize_photo, path=path, filename=filename)
        info.context.background_tasks.add_task(generate_thumbnail, path=path, filename=filename)

        if exif_info.get("gps_latitude") and exif_info.get("gps_longitude"):
            info.context.background_tasks.add_task(add_terrain_elevation_to_photo, photo=photo)

        return photo


@strawberry.type
class EditPhotoMutation:
    @strawberry.input
    class EditPhotoInput:
        name: Optional[str] = None
        description: Optional[str] = None
        point_of_interest: Optional[ComboboxInput] = None
        is_flight_cover: Optional[bool] = None

        def to_dict(self):
            return {
                key: getattr(self, key) for key in ('name', 'description', 'is_flight_cover')
                if getattr(self, key) is not None
            }

    @strawberry.mutation()
    @authenticated_user_only()
    async def edit_photo(self, info, id: int, input: EditPhotoInput) -> Photo:
        data = input.to_dict()
        async with get_session() as db:
            photo = (await db.scalars(
                BaseQueryResolver(Photo, models.Photo).get_query(user_id=info.context.user_id, object_id=id)
            )).one()

            if input.point_of_interest:
                data['point_of_interest_id'] = await handle_combobox_save(
                    db,
                    models.PointOfInterest,
                    input.point_of_interest,
                    info.context.user_id,
                    extra_data={
                        "description": ""
                    }
                )

            if input.is_flight_cover:
                # reset other covers
                (await db.execute(
                    update(models.Photo)
                    .filter(models.Photo.flight_id == photo.flight_id)
                    .filter(models.Photo.id != id).values(is_flight_cover=False))
                 )

            updated_model = await models.Photo.update(db, obj=photo, data=data)
            return Photo(**updated_model.as_dict())

    @strawberry.mutation()
    @authenticated_user_only()
    async def rotate_photo(self, info, id: int, angle: int) -> Photo:
        async with get_session() as db:
            photo = (await db.scalars(
                BaseQueryResolver(Photo, models.Photo).get_query(user_id=info.context.user_id, object_id=id)
            )).one()
            photo_filename = photo.filename
            photo_as_dict = photo.as_dict()

        await asyncio.gather(
            rotate_image(
                path=get_photo_basepath(photo.flight_id),
                filename=photo_filename,
                angle=angle,
            ),
            rotate_image(
                path=get_photo_basepath(photo.flight_id) + "/thumbs",
                filename=photo_filename,
                angle=angle,
            ),
        )

        return Photo(**photo_as_dict)


@strawberry.type
class DeletePhotoMutation:
    @strawberry.mutation()
    @authenticated_user_only()
    async def delete_photo(self, info, id: int) -> Photo:
        photo = await BaseMutationResolver(Photo, models.Photo).delete(user_id=info.context.user_id, id=id)

        base_path = get_photo_basepath(photo.flight_id)
        delete_file(f"{base_path}/{photo.filename}", silent=True)
        delete_file(f"{base_path}/thumbs/{photo.filename}", silent=True)

        return photo
