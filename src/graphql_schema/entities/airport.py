from typing import List
import strawberry
from sqlalchemy import select, or_
from database import models
from decorators.endpoints import authenticated_user_only
from dependencies.db import get_session
from graphql_schema.sqlalchemy_to_strawberry_type import strawberry_sqlalchemy_type


@strawberry_sqlalchemy_type(models.Airport)
class Airport:
    pass


def get_base_query(user_id: int):
    return (
        select(models.Airport)
        .filter(models.Airport.deleted.is_(False))
        .filter(or_(
            models.Airport.created_by_id == user_id,
            models.Airport.created_by_id.is_(None),
        ))
        .order_by(models.Airport.icao_code)
    )


@strawberry.type
class AirportQueries:
    @strawberry.field()
    @authenticated_user_only()
    async def airports(root, info) -> List[Airport]:
        query = get_base_query(info.context.user_id)

        async with get_session() as db:
            airports = (await db.scalars(query)).all()
            return [Airport(**a.as_dict()) for a in airports]

    @strawberry.field()
    @authenticated_user_only()
    async def airport(root, info, id: int) -> Airport:
        query = (
            get_base_query(info.context.user_id)
            .filter(models.Airport.id == id)
        )

        async with get_session() as db:
            airport = (await db.scalars(query)).one()
            return Airport(**airport.as_dict())
