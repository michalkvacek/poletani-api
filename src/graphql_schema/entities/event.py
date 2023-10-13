from typing import List
import strawberry
from database import models
from decorators.endpoints import authenticated_user_only
from database.transaction import get_session
from graphql_schema.entities.resolvers.base import BaseQueryResolver, BaseMutationResolver
from graphql_schema.entities.types.mutation_input import CreateEventInput, EditEventInput
from graphql_schema.entities.types.types import Event


@strawberry.type
class EventQueries:
    @strawberry.field()
    @authenticated_user_only()
    async def events(root, info) -> List[Event]:
        return await BaseQueryResolver(Event, models.Event).get_list(
            info.context.user_id,
            order_by=[models.Event.date_from.desc(), models.Event.id.desc()]
        )

    @strawberry.field()
    @authenticated_user_only()
    async def event(root, info, id: int) -> Event:
        return await BaseQueryResolver(Event, models.Event).get_one(id, user_id=info.context.user_id)


@strawberry.type
class EventMutation:
    @strawberry.mutation
    @authenticated_user_only()
    async def create_event(root, info, input: CreateEventInput) -> Event:
        return await BaseMutationResolver(Event, models.Event).create(input.to_dict(), info.context.user_id)

    @strawberry.mutation
    @authenticated_user_only()
    async def edit_event(root, info, id: int, input: EditEventInput) -> Event:
        async with get_session() as db:
            event = (await db.scalars(
                BaseQueryResolver(Event, models.Event).get_query(user_id=info.context.user_id, object_id=id)
            )).one()

            updated_event = await models.Event.update(db, obj=event, data=input.to_dict())
            return Event(**updated_event.as_dict())
