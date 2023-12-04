import asyncio
from typing import List, Optional
import strawberry
from fastapi import HTTPException
from starlette.status import HTTP_401_UNAUTHORIZED
from background_jobs.weather import download_weather
from database import models
from decorators.endpoints import authenticated_user_only
from decorators.error_logging import error_logging
from database.transaction import get_session
from graphql_schema.entities.resolvers.flight import handle_aircraft_save, FlightMutationResolver, FlightQueryResolver
from graphql_schema.entities.types.mutation_input import EditFlightInput, CreateFlightInput
from .helpers.combobox import handle_combobox_save
from graphql_schema.entities.types.types import Flight


@strawberry.type
class FlightQueries:

    @strawberry.field()
    @error_logging
    async def flights(
            root, info,
            username: Optional[str] = None,
            public: Optional[bool] = False,
            copilot_id: Optional[int] = None,
            point_of_interest_id: Optional[int] = None,
            aircraft_id: Optional[int] = None,
    ) -> List[Flight]:
        if not info.context.user_id and not public:
            raise HTTPException(HTTP_401_UNAUTHORIZED)

        return await FlightQueryResolver().get_list(
            user_id=info.context.user_id,
            username=username,
            only_public=public,
            copilot_id=copilot_id,
            aircraft_id=aircraft_id,
            point_of_interest_id=point_of_interest_id

        )

    @strawberry.field()
    @error_logging
    async def flight(root, info, id: int, username: Optional[str] = None, public: Optional[bool] = False) -> Flight:
        if not info.context.user_id and not public:
            raise HTTPException(HTTP_401_UNAUTHORIZED)

        return await FlightQueryResolver().get_one(id, user_id=info.context.user_id, username=username, public=public)


@strawberry.type
class FlightMutation:
    @strawberry.mutation
    @error_logging
    @authenticated_user_only()
    async def create_flight(self, info, input: CreateFlightInput) -> Flight:
        data = input.to_dict()
        user_id = info.context.user_id
        async with get_session() as db:
            aircraft_id = await handle_aircraft_save(db, info.context.user_id, input.aircraft)

            # TODO: tohle je blbost, bude to vyrabet dve stejne instance!
            takeoff_airport_id, landing_airport_id = await asyncio.gather(
                handle_combobox_save(
                    db, models.Airport, input.takeoff_airport, user_id, name_column="icao_code",
                    extra_data={"name": input.takeoff_airport.name}
                ),
                handle_combobox_save(
                    db, models.Airport, input.landing_airport, user_id, name_column="icao_code",
                    extra_data={"name": input.landing_airport.name}
                )
            )

        data.update({
            "takeoff_airport_id": takeoff_airport_id,
            "landing_airport_id": landing_airport_id,
            "aircraft_id": aircraft_id,
            "has_terrain_elevation": False,
            "name": "",
            "description": ""
        })
        flight = await FlightMutationResolver().create(data, info.context.user_id)

        info.context.background_tasks.add_task(
            download_weather,
            flight_id=flight.id, airport_id=takeoff_airport_id, date_time=flight.takeoff_datetime, type_="takeoff"
        )
        info.context.background_tasks.add_task(
            download_weather,
            flight_id=flight.id, airport_id=landing_airport_id, date_time=flight.landing_datetime, type_="landing"
        )

        return flight

    @strawberry.mutation
    @error_logging
    @authenticated_user_only()
    async def edit_flight(self, info, id: int, input: EditFlightInput) -> Flight:
        return await FlightMutationResolver().update(info.context, id, input)

    @strawberry.mutation
    @error_logging
    @authenticated_user_only()
    async def delete_flight(self, info, id: int) -> Flight:
        return await FlightMutationResolver().delete(info.context.user_id, id)
