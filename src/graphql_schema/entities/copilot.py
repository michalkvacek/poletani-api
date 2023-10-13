from typing import List
import strawberry
from database import models
from decorators.endpoints import authenticated_user_only
from database.transaction import get_session
from graphql_schema.entities.resolvers.base import BaseQueryResolver, BaseMutationResolver
from graphql_schema.entities.types.mutation_input import CreateCopilotInput, EditCopilotInput
from graphql_schema.entities.types.types import Copilot


@strawberry.type
class CopilotQueries:
    @strawberry.field()
    @authenticated_user_only()
    async def copilots(root, info) -> List[Copilot]:
        return await BaseQueryResolver(Copilot, models.Copilot).get_list(info.context.user_id)

    @strawberry.field()
    @authenticated_user_only()
    async def copilot(root, info, id: int) -> Copilot:
        return await BaseQueryResolver(Copilot, models.Copilot).get_one(id, user_id=info.context.user_id)


@strawberry.type
class CreateCopilotMutation:
    @strawberry.mutation
    @authenticated_user_only()
    async def create_copilot(root, info, input: CreateCopilotInput) -> Copilot:
        return await BaseMutationResolver(Copilot, models.Copilot).create(
            data=input.to_dict(),
            user_id=info.context.user_id
        )


@strawberry.type
class EditCopilotMutation:
    @strawberry.mutation
    @authenticated_user_only()
    async def edit_copilot(root, info, id: int, input: EditCopilotInput) -> Copilot:
        async with get_session() as db:
            copilot = (await db.scalars(
                BaseQueryResolver(Copilot, models.Copilot).get_query(object_id=id, user_id=info.context.user_id)
            )).one()

            updated_copilot = await models.Copilot.update(db, obj=copilot, data=input.to_dict())
            return Copilot(**updated_copilot.as_dict())
