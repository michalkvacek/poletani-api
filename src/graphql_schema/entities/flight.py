import asyncio
from typing import Optional
import strawberry
from background_jobs.weather import download_weather
from database import models
from database.transaction import get_session
from decorators.endpoints import authenticated_user_only, allow_public
from decorators.error_logging import error_logging
from graphql_schema.entities.resolvers.flight import handle_aircraft_save, FlightMutationResolver, FlightQueryResolver
from graphql_schema.entities.types.mutation_input import EditFlightInput, CreateFlightInput
from graphql_schema.entities.types.types import Flight
from .helpers.combobox import handle_combobox_save
from .helpers.detail import get_detail_filters
from .helpers.pagination import PaginationWindow, get_pagination_window


@strawberry.type
class FlightQueries:

    @strawberry.field()
    @error_logging
    @allow_public
    async def flights(
            root, info,
            limit: int,
            offset: int = 0,
            username: Optional[str] = None,
            event_id: Optional[int] = None,
            public: Optional[bool] = False,
            copilot_id: Optional[int] = None,
            point_of_interest_id: Optional[int] = None,
            aircraft_id: Optional[int] = None,
    ) -> PaginationWindow[Flight]:
        query = FlightQueryResolver().get_query(
            user_id=info.context.user_id,
            username=username,
            event_id=event_id,
            only_public=public,
            copilot_id=copilot_id,
            aircraft_id=aircraft_id,
            point_of_interest_id=point_of_interest_id
        )

        return await get_pagination_window(
            query=query,
            item_type=Flight,
            limit=limit,
            offset=offset,
        )

    @strawberry.field()
    @error_logging
    @allow_public
    async def flight(
            root, info,
            id: Optional[int] = None,
            url_slug: Optional[str] = None,
            username: Optional[str] = None,
            public: Optional[bool] = False
    ) -> Flight:
        filter_params = get_detail_filters(id, url_slug)
        if username:
            filter_params['username'] = username

        return await FlightQueryResolver().get_one(
            user_id=info.context.user_id,
            only_public=public,
            **filter_params
        )


@strawberry.type
class FlightMutation:
    @strawberry.mutation
    @error_logging
    @authenticated_user_only()
    async def create_flight(self, info, input: CreateFlightInput) -> Flight:
        return await FlightMutationResolver().create(info.context, input)

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
