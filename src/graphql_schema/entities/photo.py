from typing import List
import strawberry
from sqlalchemy import select
from strawberry.file_uploads import Upload
from database import models
from graphql_schema.sqlalchemy_to_strawberry_type import strawberry_sqlalchemy_type, strawberry_sqlalchemy_input
from upload_utils import get_public_url, handle_file_upload


@strawberry_sqlalchemy_type(models.Photo)
class Photo:
    url: str = strawberry.field(resolver=lambda root: get_public_url(root.filename))
    thumbnail_url: str = strawberry.field(resolver=lambda root: get_public_url(f"thumbs/{root.filename}"))


def get_base_query(user_id: int):
    return (
        select(models.Photo)
        .filter(models.Photo.created_by_id == user_id)
        .order_by(models.Photo.id.desc())
    )


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
        photos_dest = f"/app/uploads/photos/{input.flight_id}/"
        filename = await handle_file_upload(input.photo, photos_dest)

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
    @strawberry_sqlalchemy_input(models.Photo, exclude_fields=[], all_optional=True)
    class EditPhotoInput:
        pass

    @strawberry.mutation
    async def update_photo(self, info, input: EditPhotoInput) -> Photo:
        query = get_base_query(info.context.user_id)
        photo = info.context.db.scalars(query.filter(models.Photo.id == input.id))

        update_data = input.to_dict()
        photo.update(**update_data)

        return photo


@strawberry.type
class DeletePhotoMutation:
    @strawberry.input
    class DeletePhotoInput:
        id: int

    @strawberry.mutation
    async def delete_photo(self, info, input: DeletePhotoInput) -> Photo:
        pass
