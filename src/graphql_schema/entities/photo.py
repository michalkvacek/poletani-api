from typing import List, Optional
import strawberry
from database import models
from decorators.endpoints import authenticated_user_only, allow_public
from decorators.error_logging import error_logging
from graphql_schema.entities.resolvers.base import BaseQueryResolver
from graphql_schema.entities.resolvers.photo import PhotoMutationResolver, PhotoQueryResolver
from graphql_schema.entities.types.types import Photo
from graphql_schema.entities.types.mutation_input import EditPhotoInput, UploadPhotoInput, AdjustmentInput


@strawberry.type
class PhotoQueries:
    @strawberry.field()
    @error_logging
    @allow_public
    async def photos(
            root, info,
            flight_id: Optional[int] = None,
            copilot_id: Optional[int] = None,
            point_of_interest_id: Optional[int] = None,
            aircraft_id: Optional[int] = None,
            public: Optional[bool] = False,
    ) -> List[Photo]:
        return await PhotoQueryResolver().get_list(
            public=public,
            flight_id=flight_id,
            user_id=info.context.user_id,
            copilot_id=copilot_id,
            aircraft_id=aircraft_id,
            point_of_interest_id=point_of_interest_id,
        )

    @strawberry.field()
    @error_logging
    @allow_public
    async def photo(root, info, id: int, public: Optional[bool] = False,) -> Photo:
        return await BaseQueryResolver(Photo, models.Photo).get_one(id, user_id=info.context.user_id, public=public)


@strawberry.type
class PhotoMutation:
    @strawberry.mutation
    @error_logging
    @authenticated_user_only()
    async def upload_photo(self, info, input: UploadPhotoInput) -> Photo:
        return await PhotoMutationResolver().upload(info, input)

    @strawberry.mutation()
    @error_logging
    @authenticated_user_only()
    async def edit_photo(self, info, id: int, input: EditPhotoInput) -> Photo:
        return await PhotoMutationResolver().update(id, input, info.context.user_id)

    @strawberry.mutation()
    @error_logging
    @authenticated_user_only()
    async def change_orientation(self, info, id: int, direction: str) -> Photo:
        return await PhotoMutationResolver().change_orientation(
            id=id,
            user_id=info.context.user_id,
            direction=direction,
            info=info
        )

    @strawberry.mutation()
    @error_logging
    @authenticated_user_only()
    async def adjust_photo(self, info, id: int, adjustment: AdjustmentInput) -> Photo:
        return await PhotoMutationResolver().adjust(id, info=info, user_id=info.context.user_id, adjustment=adjustment)

    @strawberry.mutation()
    @error_logging
    @authenticated_user_only()
    async def delete_photo(self, info, id: int) -> Photo:
        return await PhotoMutationResolver().delete(user_id=info.context.user_id, id=id)
