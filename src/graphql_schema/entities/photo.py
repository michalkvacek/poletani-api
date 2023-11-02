from typing import List
import strawberry
from database import models
from decorators.endpoints import authenticated_user_only
from graphql_schema.entities.resolvers.base import BaseQueryResolver
from graphql_schema.entities.resolvers.photo import PhotoMutationResolver
from graphql_schema.entities.types.types import Photo
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
        return await PhotoMutationResolver().upload(info, input)

    @strawberry.mutation()
    @authenticated_user_only()
    async def edit_photo(self, info, id: int, input: EditPhotoInput) -> Photo:
        return await PhotoMutationResolver().update(id, input, info.context.user_id)

    @strawberry.mutation()
    @authenticated_user_only()
    async def change_orientation(self, info, id: int, direction: str) -> Photo:
        return await PhotoMutationResolver().change_orientation(
            id=id,
            user_id=info.context.user_id,
            direction=direction,
            info=info
        )

    @strawberry.mutation()
    @authenticated_user_only()
    async def adjust_photo(self, info, id: int, adjustment: AdjustmentInput) -> Photo:
        return await PhotoMutationResolver().adjust(id, info=info, user_id=info.context.user_id, adjustment=adjustment)

    @strawberry.mutation()
    @authenticated_user_only()
    async def delete_photo(self, info, id: int) -> Photo:
        return await PhotoMutationResolver().delete(user_id=info.context.user_id, id=id)
