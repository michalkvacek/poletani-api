from typing import List, TYPE_CHECKING
import strawberry
from database import models
from decorators.endpoints import authenticated_user_only
from dependencies.db import get_session
from graphql_schema.sqlalchemy_to_strawberry_type import strawberry_sqlalchemy_input
from .resolvers.base import get_base_resolver, get_list, get_one
from graphql_schema.entities.types.types import Event

if TYPE_CHECKING:
    pass


@strawberry.type
class EventQueries:
    @strawberry.field()
    @authenticated_user_only()
    async def events(root, info) -> List[Event]:
        query = get_base_resolver(
            models.Event, user_id=info.context.user_id,
            order_by=[models.Event.date_from.desc(), models.Event.id.desc()]
        )
        return await get_list(models.Event, query)

    @strawberry.field()
    @authenticated_user_only()
    async def event(root, info, id: int) -> Event:
        query = get_base_resolver(models.Event, user_id=info.context.user_id, object_id=id)
        return await get_one(models.Event, query)


@strawberry.type
class CreateEventMutation:
    @strawberry_sqlalchemy_input(model=models.Event, exclude_fields=["id"])
    class CreateEventInput:
        pass

    @strawberry.mutation
    @authenticated_user_only()
    async def create_event(root, info, input: CreateEventInput) -> Event:
        input_data = input.to_dict()
        async with get_session() as db:
            event = await models.Event.create(
                db,
                data=dict(
                    **input_data,
                    created_by_id=info.context.user_id,
                )
            )

            return Event(**event.as_dict())


@strawberry.type
class EditEventMutation:
    @strawberry_sqlalchemy_input(model=models.Event, exclude_fields=["id"])
    class EditEventInput:
        pass

    @strawberry.mutation
    @authenticated_user_only()
    async def edit_event(root, info, id: int, input: EditEventInput) -> Event:
        async with get_session() as db:
            event = (await db.scalars(
                get_base_resolver(models.Event, user_id=info.context.user_id, object_id=id)
            )).one()

            updated_event = await models.Event.update(db, obj=event, data=input.to_dict())
            return Event(**updated_event.as_dict())
