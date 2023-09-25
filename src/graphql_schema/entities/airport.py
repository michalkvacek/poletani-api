from typing import List
import strawberry
from database import models
from decorators.endpoints import authenticated_user_only
from graphql_schema.entities.resolvers.base import get_list, get_one, get_base_resolver
from graphql_schema.sqlalchemy_to_strawberry_type import strawberry_sqlalchemy_type


@strawberry_sqlalchemy_type(models.Airport)
class Airport:
    pass


@strawberry.type
class AirportQueries:
    @strawberry.field()
    @authenticated_user_only()
    async def airports(root, info) -> List[Airport]:
        query = get_base_resolver(models.Airport, user_id=info.context.user_id)
        return await get_list(models.Airport, query)

    @strawberry.field()
    @authenticated_user_only()
    async def airport(root, info, id: int) -> Airport:
        query = get_base_resolver(models.Airport, user_id=info.context.user_id, object_id=id)
        return await get_one(models.Airport, query)
