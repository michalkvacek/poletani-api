from typing import List
import strawberry
from database import models
from decorators.error_logging import error_logging
from decorators.endpoints import authenticated_user_only
from graphql_schema.entities.resolvers.base import BaseQueryResolver
from graphql_schema.entities.types.types import Airport


@strawberry.type
class AirportQueries:
    @strawberry.field()
    @error_logging
    @authenticated_user_only()
    async def airports(root, info) -> List[Airport]:
        return await BaseQueryResolver(Airport, models.Airport).get_list(info.context.user_id)

    @strawberry.field()
    @error_logging
    @authenticated_user_only()
    async def airport(root, info, id: int) -> Airport:
        return await BaseQueryResolver(Airport, models.Airport).get_one(
            object_id=id,
            user_id=info.context.user_id
        )
