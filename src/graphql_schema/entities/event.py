from typing import List, Optional
import strawberry
from fastapi import HTTPException
from starlette.status import HTTP_401_UNAUTHORIZED
from database import models
from decorators.endpoints import authenticated_user_only
from graphql_schema.entities.resolvers.base import BaseMutationResolver
from graphql_schema.entities.resolvers.event import EventQueryResolver
from graphql_schema.entities.types.mutation_input import CreateEventInput, EditEventInput
from graphql_schema.entities.types.types import Event


@strawberry.type
class EventQueries:
    @strawberry.field()
    async def events(root, info, username: Optional[str] = None) -> List[Event]:
        if not info.context.user_id and not username:
            raise HTTPException(HTTP_401_UNAUTHORIZED)

        return await EventQueryResolver().get_list(
            info.context.user_id,
            username=username,
            order_by=[models.Event.date_from.desc(), models.Event.id.desc()]
        )

    @strawberry.field()
    async def event(root, info, id: int, username: Optional[str] = None) -> Event:
        if not info.context.user_id and not username:
            raise HTTPException(HTTP_401_UNAUTHORIZED)

        return await EventQueryResolver().get_one(
            id,
            username=username,
            user_id=info.context.user_id
        )


@strawberry.type
class EventMutation:
    @strawberry.mutation
    @authenticated_user_only()
    async def create_event(root, info, input: CreateEventInput) -> Event:
        return await BaseMutationResolver(Event, models.Event).create(input.to_dict(), info.context.user_id)

    @strawberry.mutation
    @authenticated_user_only()
    async def edit_event(root, info, id: int, input: EditEventInput) -> Event:
        return await BaseMutationResolver(Event, models.Event).update(id, input, info.context.user_id)
