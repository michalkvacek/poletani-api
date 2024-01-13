from typing import List, Optional
import strawberry
from strawberry.types import Info
from database import models
from decorators.error_logging import error_logging
from decorators.endpoints import authenticated_user_only, allow_public
from graphql_schema.entities.helpers.detail import get_detail_filters
from graphql_schema.entities.resolvers.base import BaseMutationResolver
from graphql_schema.entities.resolvers.copilot import CopilotQueryResolver
from graphql_schema.entities.types.mutation_input import CreateCopilotInput, EditCopilotInput
from graphql_schema.entities.types.types import Copilot


@strawberry.type
class CopilotQueries:
    @strawberry.field()
    @error_logging
    @authenticated_user_only()
    async def copilots(root, info: Info) -> List[Copilot]:
        return await CopilotQueryResolver().get_list(info.context.user_id)

    @strawberry.field()
    @error_logging
    @allow_public
    async def copilot(
            root, info: Info,
            id: Optional[int] = None,
            url_slug: Optional[str] = None,
            pilot_username: Optional[str] = None,
            public: Optional[bool] = False
    ) -> Copilot:

        filter_params = get_detail_filters(id, url_slug)
        if pilot_username:
            filter_params['pilot_username'] = pilot_username

        return await CopilotQueryResolver().get_one(
            user_id=info.context.user_id,
            only_public=public,
            **filter_params
        )


@strawberry.type
class CopilotMutation:
    @strawberry.mutation
    @error_logging
    @authenticated_user_only()
    async def create_copilot(root, info, input: CreateCopilotInput) -> Copilot:
        return await BaseMutationResolver(Copilot, models.Copilot).create(info.context, data=input)

    @strawberry.mutation
    @error_logging
    @authenticated_user_only()
    async def edit_copilot(root, info, id: int, input: EditCopilotInput) -> Copilot:
        return await BaseMutationResolver(Copilot, models.Copilot).update(id, input, info.context.user_id)
