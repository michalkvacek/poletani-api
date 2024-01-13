from typing import List, Optional
import strawberry
from database import models
from decorators.endpoints import authenticated_user_only, allow_public
from decorators.error_logging import error_logging
from graphql_schema.entities.helpers.detail import get_detail_filters
from graphql_schema.entities.helpers.pagination import PaginationWindow, get_pagination_window
from graphql_schema.entities.resolvers.base import BaseMutationResolver
from graphql_schema.entities.resolvers.event import EventQueryResolver
from graphql_schema.entities.types.mutation_input import CreateEventInput, EditEventInput
from graphql_schema.entities.types.types import Event


@strawberry.type
class EventQueries:
    @strawberry.field()
    @error_logging
    @allow_public
    async def events(
            root,
            info,
            limit: int,
            offset: int = 0,
            username: Optional[str] = None,
            public: Optional[bool] = False,
    ) -> PaginationWindow[Event]:
        query = EventQueryResolver().get_query(
            info.context.user_id,
            username=username,
            order_by=[models.Event.date_from.desc(), models.Event.id.desc()],
            public=public
        )

        return await get_pagination_window(
            query=query,
            item_type=Event,
            limit=limit,
            offset=offset
        )

    @strawberry.field()
    @error_logging
    @allow_public
    async def event(
            root, info,
            id: Optional[int] = None,
            url_slug: Optional[str] = None,
            username: Optional[str] = None,
            public: Optional[bool] = False
    ) -> Event:
        filter_params = get_detail_filters(id, url_slug)
        if username:
            filter_params['username'] = username

        return await EventQueryResolver().get_one(
            public=public,
            user_id=info.context.user_id ,
                    ** filter_params
        )


@strawberry.type
class EventMutation:
    @strawberry.mutation
    @error_logging
    @authenticated_user_only()
    async def create_event(root, info, input: CreateEventInput) -> Event:
        return await BaseMutationResolver(Event, models.Event).create(info.context, input)

    @strawberry.mutation
    @error_logging
    @authenticated_user_only()
    async def edit_event(root, info, id: int, input: EditEventInput) -> Event:
        return await BaseMutationResolver(Event, models.Event).update(id, input, info.context.user_id)
