from typing import List, Annotated, TYPE_CHECKING
import strawberry
from sqlalchemy import select
from database import models
from graphql_schema.dataloaders.flight import flights_by_copilot_dataloader
from graphql_schema.sqlalchemy_to_strawberry_type import strawberry_sqlalchemy_type

if TYPE_CHECKING:
    from .flight import Flight

@strawberry_sqlalchemy_type(models.Copilot)
class CopilotType:
    async def load_flights(root):
        return await flights_by_copilot_dataloader.load(root.id)

    flights: List[Annotated["Flight", strawberry.lazy('.flight')]] = strawberry.field(resolver=load_flights)


def get_base_query(user_id: int):
    return (
        select(models.Copilot)
        .filter(models.Copilot.created_by_id == user_id)
        .filter(models.Copilot.deleted.is_(False))
        .order_by(models.Copilot.id.desc())
    )


@strawberry.type
class CopilotQueries:
    @strawberry.field
    async def copilots(root, info) -> List[CopilotType]:
        return (await info.context.db.scalars(
            get_base_query(info.context.user_id)
        )).all()

    @strawberry.field
    async def copilot(root, info, id: int) -> CopilotType:
        return (await info.context.db.scalars(
            get_base_query(info.context.user_id)
            .filter(models.Copilot.id == id)
        )).one()
