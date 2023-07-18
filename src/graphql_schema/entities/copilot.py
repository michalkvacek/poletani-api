from typing import List
import strawberry
from sqlalchemy import select
from database.models import Copilot
from graphql_schema.sqlalchemy_to_strawberry_type import strawberry_sqlalchemy_type


@strawberry_sqlalchemy_type(Copilot)
class CopilotType:
    pass


@strawberry.type
class CopilotQueries:
    @strawberry.field
    async def copilots(root, info) -> List[CopilotType]:
        return (await info.context.db.scalars(select(Copilot))).all()
