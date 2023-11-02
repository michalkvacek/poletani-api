from typing import List, Optional
import strawberry
from fastapi import HTTPException
from starlette.status import HTTP_401_UNAUTHORIZED

from database import models
from decorators.endpoints import authenticated_user_only
from graphql_schema.entities.resolvers.base import BaseMutationResolver
from graphql_schema.entities.resolvers.copilot import CopilotQueryResolver
from graphql_schema.entities.types.mutation_input import CreateCopilotInput, EditCopilotInput
from graphql_schema.entities.types.types import Copilot


@strawberry.type
class CopilotQueries:
    @strawberry.field()
    @authenticated_user_only()
    async def copilots(root, info) -> List[Copilot]:
        return await CopilotQueryResolver().get_list(info.context.user_id)

    @strawberry.field()
    async def copilot(root, info, id: int, pilot_username: Optional[str] = None) -> Copilot:
        if not info.context.user_id and not pilot_username:
            raise HTTPException(HTTP_401_UNAUTHORIZED)

        return await CopilotQueryResolver().get_one(
            id,
            user_id=info.context.user_id,
            pilot_username=pilot_username
        )


@strawberry.type
class CopilotMutation:
    @strawberry.mutation
    @authenticated_user_only()
    async def create_copilot(root, info, input: CreateCopilotInput) -> Copilot:
        return await BaseMutationResolver(Copilot, models.Copilot).create(
            data=input.to_dict(),
            user_id=info.context.user_id
        )

    @strawberry.mutation
    @authenticated_user_only()
    async def edit_copilot(root, info, id: int, input: EditCopilotInput) -> Copilot:
        return await BaseMutationResolver(Copilot, models.Copilot).update(id, input, info.context.user_id)
