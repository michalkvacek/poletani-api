from typing import List, Annotated, TYPE_CHECKING
import strawberry
from sqlalchemy import select
from database import models
from decorators.endpoints import authenticated_user_only
from dependencies.db import get_session
from graphql_schema.dataloaders.flight import flights_by_copilot_dataloader
from graphql_schema.sqlalchemy_to_strawberry_type import strawberry_sqlalchemy_type, strawberry_sqlalchemy_input

if TYPE_CHECKING:
    from .flight import Flight


@strawberry_sqlalchemy_type(models.Copilot)
class Copilot:
    async def load_flights(root):
        return await flights_by_copilot_dataloader.load(root.id)

    flights: List[Annotated["Flight", strawberry.lazy('.flight')]] = strawberry.field(resolver=load_flights)


def get_base_query(user_id: int):
    return (
        select(models.Copilot)
        .filter(models.Copilot.created_by_id == user_id)
        .filter(models.Copilot.deleted.is_(False))
        .order_by(models.Copilot.name)
    )


@strawberry.type
class CopilotQueries:
    @strawberry.field()
    @authenticated_user_only()
    async def copilots(root, info) -> List[Copilot]:
        async with get_session() as db:
            copilots = (await db.scalars(
                get_base_query(info.context.user_id)
            )).all()

            return [Copilot(**c.as_dict()) for c in copilots]

    @strawberry.field()
    @authenticated_user_only()
    async def copilot(root, info, id: int) -> Copilot:
        async with get_session() as db:
            copilot = (await db.scalars(
                get_base_query(info.context.user_id)
                .filter(models.Copilot.id == id)
            )).one()
            return Copilot(**copilot.as_dict())


@strawberry.type
class CreateCopilotMutation:
    @strawberry_sqlalchemy_input(model=models.Copilot, exclude_fields=["id"])
    class CreateCopilotInput:
        pass

    @strawberry.mutation
    @authenticated_user_only()
    async def create_copilot(root, info, input: CreateCopilotInput) -> Copilot:
        input_data = input.to_dict()
        async with get_session() as db:
            copilot = await models.Copilot.create(
                db,
                data=dict(
                    **input_data,
                    created_by_id=info.context.user_id,
                )
            )

            return Copilot(**copilot.as_dict())


@strawberry.type
class EditCopilotMutation:
    @strawberry_sqlalchemy_input(model=models.Copilot, exclude_fields=["id"])
    class EditCopilotInput:
        pass

    @strawberry.mutation
    @authenticated_user_only()
    async def edit_copilot(root, info, id: int, input: EditCopilotInput) -> Copilot:
        async with get_session() as db:
            copilot = (await db.scalars(
                get_base_query(info.context.user_id).filter(models.Copilot.id == id)
            )).one()

            updated_copilot = await models.Copilot.update(db, obj=copilot, data=input.to_dict())
            return Copilot(**updated_copilot.as_dict())
