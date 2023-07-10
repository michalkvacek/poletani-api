from typing import List
import strawberry
from sqlalchemy import select
from strawberry.file_uploads import Upload
from database import models
from graphql_schema.sqlalchemy_to_strawberry_type import strawberry_sqlalchemy_type, strawberry_sqlalchemy_input
from upload_utils import get_public_url, handle_file_upload, delete_file


@strawberry_sqlalchemy_type(models.Photo)
class Photo:
    url: str = strawberry.field(
        resolver=lambda root: get_public_url(f"photos/{root.flight_id}/{root.filename}")
    )
    thumbnail_url: str = strawberry.field(
        resolver=lambda root: get_public_url(f"photos/{root.flight_id}/{root.filename}")  # TODO: doplnit thumb!
    )


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
    @strawberry.field
    async def photos(root, info) -> List[Photo]:
        query = get_base_query(info.context.user_id)
        return (await info.context.db.scalars(query)).all()


@strawberry.type
class UploadPhotoMutation:
    @strawberry_sqlalchemy_input(models.Photo, exclude_fields=["id", "filename"])
    class UploadPhotoInput:
        photo: Upload

    @strawberry.mutation
    async def upload_photo(self, info, input: UploadPhotoInput) -> Photo:
        filename = await handle_file_upload(input.photo, get_photo_basepath(input.flight_id))

        # todo: udelat nahled do thumbs slozky

        created_photo = await models.Photo.create(data={
            "flight_id": input.flight_id,
            "name": input.name,
            "filename": filename,
            "description": input.description,
            "created_by_id": info.context.user_id,
        }, db_session=info.context.db)

        return created_photo


@strawberry.type
class EditPhotoMutation:
    @strawberry_sqlalchemy_input(models.Photo, exclude_fields=["id"], all_optional=True)
    class EditPhotoInput:
        pass

    @strawberry.mutation
    async def edit_photo(self, info, id: int, input: EditPhotoInput) -> Photo:
        query = get_base_query(info.context.user_id)
        photo = (await info.context.db.scalars(query.filter(models.Photo.id == id))).one()

        return await models.Photo.update(info.context.db, obj=photo, data=input.to_dict())


@strawberry.type
class DeletePhotoMutation:
    @strawberry.mutation
    async def delete_photo(self, info, id: int) -> Photo:
        query = get_base_query(info.context.user_id)
        photo = (await info.context.db.scalars(query.filter(models.Photo.id == id))).one()

        base_path = get_photo_basepath(photo.flight_id)
        try:
            delete_file(f"{base_path}/{photo.filename}")
            # TODO: odstranit nahledy
        except Exception as e:
            print("ERROR", e)

        await info.context.db.delete(photo)

        return photo
