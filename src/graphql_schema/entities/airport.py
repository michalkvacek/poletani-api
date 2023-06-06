from typing import List
import strawberry
from sqlalchemy import select
from database import models
from graphql_schema.sqlalchemy_to_strawberry_type import strawberry_sqlalchemy_type


@strawberry_sqlalchemy_type(models.Airport)
class Airport:
    pass


def get_base_query(user_id: int):
    return (
        select(models.Airport)
        .filter(models.Airport.deleted.is_(False))
    )


@strawberry.type
class AirportQueries:

    @strawberry.field
    async def airports(root, info) -> List[Airport]:
        query = (
            get_base_query(info.context.user_id)
            .order_by(models.Airport.id.desc())
        )

        return (await info.context.db.scalars(query)).all()

    @strawberry.field
    async def airport(root, info, id: int) -> Airport:
        query = (
            get_base_query(info.context.user_id)
            .filter(models.Airport.id == id)
        )
        return (await info.context.db.scalars(query)).one()
