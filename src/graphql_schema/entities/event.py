from typing import List, Optional
import strawberry
from database import models
from decorators.endpoints import authenticated_user_only, allow_public
from decorators.error_logging import error_logging
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
    async def event(root, info, id: int, username: Optional[str] = None, public: Optional[bool] = False) -> Event:
        return await EventQueryResolver().get_one(
            id,
            username=username,
            public=public,
            user_id=info.context.user_id
        )


@strawberry.type
class EventMutation:
    @strawberry.mutation
    @error_logging
    @authenticated_user_only()
    async def create_event(root, info, input: CreateEventInput) -> Event:
        return await BaseMutationResolver(Event, models.Event).create(input.to_dict(), info.context.user_id)

    @strawberry.mutation
    @error_logging
    @authenticated_user_only()
    async def edit_event(root, info, id: int, input: EditEventInput) -> Event:
        return await BaseMutationResolver(Event, models.Event).update(id, input, info.context.user_id)
