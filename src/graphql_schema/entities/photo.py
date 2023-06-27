from typing import List, Optional
import strawberry
from sqlalchemy import select
from database import models
from graphql_schema.sqlalchemy_to_strawberry_type import strawberry_sqlalchemy_type, strawberry_sqlalchemy_input


@strawberry_sqlalchemy_type(models.Photo)
class Photo:
    pass


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
class DeletePhotoMutation:

    @strawberry.input
    class DeletePhotoInput:
        id: int

    @strawberry_sqlalchemy_input(models.Photo, exclude_fields=[], all_optional=True)
    class UpdatePhotoInput:
        pass

    @strawberry.mutation
    async def update_photo(self, info, input: UpdatePhotoInput) -> Photo:
        query = get_base_query(info.context.user_id)
        photo = info.context.db.scalars(query.filter(models.Photo.id == input.id))

        update_data = input.to_dict()
        photo.update(**update_data)

        return photo

    @strawberry.mutation
    async def delete_photo(self, info, input: DeletePhotoInput) -> Photo:
        pass
