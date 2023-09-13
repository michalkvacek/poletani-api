from typing import List, Optional, Annotated, TYPE_CHECKING
import strawberry
from sqlalchemy import select, update
from strawberry.file_uploads import Upload
from background_jobs.photo import add_terrain_elevation
from database import models
from decorators.endpoints import authenticated_user_only
from dependencies.db import get_session
from graphql_schema.dataloaders.poi import poi_dataloader
from graphql_schema.sqlalchemy_to_strawberry_type import strawberry_sqlalchemy_type
from graphql_schema.types import ComboboxInput
from upload_utils import (
    get_public_url, handle_file_upload, delete_file, parse_exif_info, generate_thumbnail, file_exists, resize_image
)
from .helpers.flight import handle_combobox_save

if TYPE_CHECKING:
    from .poi import PointOfInterest


@strawberry_sqlalchemy_type(models.Photo)
class Photo:
    def resolve_url(root):
        return get_public_url(f"photos/{root.flight_id}/{root.filename}")

    def resolve_thumb_url(root):
        thumbnail = get_photo_basepath(root.flight_id) + "/thumbs/" + root.filename
        if not file_exists(thumbnail):
            return get_public_url(f"photos/{root.flight_id}/{root.filename}")

        return get_public_url(f"photos/{root.flight_id}/thumbs/{root.filename}")

    async def load_poi(root):
        if not root.point_of_interest_id:
            return None

        return await poi_dataloader.load(root.point_of_interest_id)

    url: str = strawberry.field(resolver=resolve_url)
    thumbnail_url: str = strawberry.field(resolver=resolve_thumb_url)
    point_of_interest: Optional[Annotated["PointOfInterest", strawberry.lazy('.poi')]] = strawberry.field(resolver=load_poi)  # noqa


def get_base_query(user_id: int):
    return (
        select(models.Photo)
        .filter(models.Photo.created_by_id == user_id)
        .order_by(models.Photo.id.desc())
    )


def get_photo_basepath(flight_id: int) -> str:
    return f"/app/uploads/photos/{flight_id}"


@strawberry.type
class PhotoQueries:
    @strawberry.field()
    async def photos(root, info) -> List[Photo]:
        query = get_base_query(info.context.user_id)

        async with get_session() as db:
            photos = (await db.scalars(query)).all()
            return [Photo(**photo.as_dict()) for photo in photos]


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
                "exposed_at": exif_info.get("datetime"),
                "gps_latitude": exif_info.get("gps_latitude"),
                "gps_longitude": exif_info.get("gps_longitude"),
                "gps_altitude": exif_info.get("gps_altitude"),
                "is_flight_cover": False,
                "created_by_id": info.context.user_id,
            }, db_session=db)
            photo = Photo(**photo_model.as_dict())

        info.context.background_tasks.add_task(resize_image, path=path, filename=filename, new_width=2500, quality=85)
        info.context.background_tasks.add_task(generate_thumbnail, path=path, filename=filename)

        if exif_info.get("gps_latitude") and exif_info.get("gps_longitude"):
            info.context.background_tasks.add_task(add_terrain_elevation, photo=photo)

        return photo


@strawberry.type
class EditPhotoMutation:
    @strawberry.input
    class EditPhotoInput:
        name: Optional[str] = None
        description: Optional[str] = None
        point_of_interest: Optional[ComboboxInput] = None
        is_flight_cover: Optional[bool] = None

    @strawberry.mutation()
    @authenticated_user_only()
    async def edit_photo(self, info, id: int, input: EditPhotoInput) -> Photo:
        query = get_base_query(info.context.user_id)

        data = {
            key: getattr(input, key) for key in ('name', 'description', 'is_flight_cover')
            if getattr(input, key) is not None
        }

        async with get_session() as db:
            photo = (await db.scalars(query.filter(models.Photo.id == id))).one()

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


@strawberry.type
class DeletePhotoMutation:
    @strawberry.mutation()
    @authenticated_user_only()
    async def delete_photo(self, info, id: int) -> Photo:
        query = get_base_query(info.context.user_id)
        async with get_session() as db:
            photo_model = (await db.scalars(query.filter(models.Photo.id == id))).one()
            await db.delete(photo_model)
            photo = Photo(**photo_model.as_dict())

        base_path = get_photo_basepath(photo.flight_id)
        delete_file(f"{base_path}/{photo.filename}", silent=True)
        delete_file(f"{base_path}/thumbs/{photo.filename}", silent=True)

        return photo_model
