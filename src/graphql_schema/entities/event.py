from typing import List, Annotated, TYPE_CHECKING
import strawberry
from sqlalchemy import select
from database import models
from decorators.endpoints import authenticated_user_only
from dependencies.db import get_session
from graphql_schema.dataloaders.flight import flights_by_event_dataloader
from graphql_schema.sqlalchemy_to_strawberry_type import strawberry_sqlalchemy_type, strawberry_sqlalchemy_input

if TYPE_CHECKING:
    from .flight import Flight


@strawberry_sqlalchemy_type(models.Event)
class Event:
    async def load_flights(root):
        return await flights_by_event_dataloader.load(root.id)

    flights: List[Annotated["Flight", strawberry.lazy('.flight')]] = strawberry.field(resolver=load_flights)


def get_base_query(user_id: int):
    return (
        select(models.Event)
        .filter(models.Event.created_by_id == user_id)
        .filter(models.Event.deleted.is_(False))
        .order_by(models.Event.date_from.desc(), models.Event.id.desc())
    )


@strawberry.type
class EventQueries:
    @strawberry.field()
    @authenticated_user_only()
    async def events(root, info) -> List[Event]:
        async with get_session() as db:
            events = (await db.scalars(
                get_base_query(info.context.user_id)
            )).all()

            return [Event(**c.as_dict()) for c in events]

    @strawberry.field()
    @authenticated_user_only()
    async def event(root, info, id: int) -> Event:
        async with get_session() as db:
            event = (await db.scalars(
                get_base_query(info.context.user_id)
                .filter(models.Event.id == id)
            )).one()
            return Event(**event.as_dict())


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
                get_base_query(info.context.user_id).filter(models.Event.id == id)
            )).one()

            updated_event = await models.Event.update(db, obj=event, data=input.to_dict())
            return Event(**updated_event.as_dict())
