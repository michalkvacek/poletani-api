import asyncio
from typing import List, Optional
import strawberry
from fastapi import HTTPException
from sqlalchemy import select
from starlette.status import HTTP_401_UNAUTHORIZED
from database import models
from decorators.endpoints import authenticated_user_only
from decorators.error_logging import error_logging
from dependencies.db import get_session
from graphql_schema.entities.resolvers.flight import (
    handle_aircraft_save, handle_weather_info, FlightMutationResolver, get_airport,
)
from graphql_schema.entities.types.mutation_input import EditFlightInput, CreateFlightInput
from .resolvers.base import get_list, get_one
from graphql_schema.entities.types.types import Flight


def get_base_query(user_id: Optional[int], username: Optional[str] = None, is_auth: bool = False):
    query = (
        select(models.Flight)
        .filter(models.Flight.deleted.is_(False))
        .order_by(models.Flight.takeoff_datetime.desc())
    )

    if user_id:
        query = query.filter(models.Flight.created_by_id == user_id)

    if username:
        query = (
            query
            .join(models.Flight.created_by)
            .filter(models.User.public_username == username)
        )

    if not is_auth:
        query = query.filter(models.Flight.is_public.is_(True))

    return query


@strawberry.type
class FlightQueries:

    @strawberry.field()
    async def flights(root, info, username: Optional[str] = None) -> List[Flight]:
        if not info.context.user_id and not username:
            raise HTTPException(HTTP_401_UNAUTHORIZED)

        query = (
            get_base_query(user_id=info.context.user_id, username=username, is_auth=bool(info.context.user_id))
            .order_by(models.Flight.id.desc())
        )
        return await get_list(models.Flight, query)

    @strawberry.field()
    @error_logging
    async def flight(root, info, id: int, username: Optional[str] = None) -> Flight:
        if not info.context.user_id and not username:
            raise HTTPException(HTTP_401_UNAUTHORIZED)

        query = (
            get_base_query(user_id=info.context.user_id, username=username, is_auth=bool(info.context.user_id))
            .filter(models.Flight.id == id)
        )
        return await get_one(models.Flight, query)


@strawberry.type
class FlightMutation:
    @strawberry.mutation
    @authenticated_user_only()
    async def create_flight(self, info, input: CreateFlightInput) -> Flight:
        data = input.to_dict()

        async with (get_session() as db):
            takeoff_airport = await get_airport(db, input.takeoff_airport, info.context.user_id)
            landing_airport = await get_airport(db, input.landing_airport, info.context.user_id)

            aircraft_id = await handle_aircraft_save(db, info.context.user_id, input.aircraft)
            weather_takeoff, weather_landing = await asyncio.gather(
                handle_weather_info(db, data['takeoff_datetime'], takeoff_airport),
                handle_weather_info(db, data['landing_datetime'], landing_airport)
            )
            await db.flush()

            flight = await models.Flight.create(db, data={
                **data,
                "takeoff_weather_info_id": weather_takeoff.id if weather_takeoff else None,
                "landing_weather_info_id": weather_landing.id if weather_landing else None,
                "takeoff_airport_id": takeoff_airport.id,
                "landing_airport_id": landing_airport.id,
                "has_terrain_elevation": False,
                "aircraft_id": aircraft_id,
                "created_by_id": info.context.user_id
            })
            return Flight(**flight.as_dict())

    @strawberry.mutation
    @authenticated_user_only()
    async def edit_flight(self, info, id: int, input: EditFlightInput) -> Flight:
        return await FlightMutationResolver.update(info.context, id, input)

    @strawberry.mutation
    @authenticated_user_only()
    async def delete_flight(self, info, id: int) -> Flight:
        return await FlightMutationResolver.delete(info.context.user_id, id)
