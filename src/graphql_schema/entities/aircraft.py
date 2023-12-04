from typing import List, Optional
import strawberry
from fastapi import HTTPException
from starlette.status import HTTP_401_UNAUTHORIZED

from decorators.endpoints import authenticated_user_only
from decorators.error_logging import error_logging
from .resolvers.aircraft import AircraftMutationResolver, AircraftQueryResolver
from graphql_schema.entities.types.mutation_input import CreateAircraftInput, EditAircraftInput
from graphql_schema.entities.types.types import Aircraft


@strawberry.type
class AircraftQueries:
    @strawberry.field()
    @error_logging
    @authenticated_user_only()
    async def aircrafts(root, info) -> List[Aircraft]:
        return await AircraftQueryResolver().get_list(
            info.context.user_id,
            organization_ids=info.context.organization_ids
        )

    @strawberry.field()
    @error_logging
    async def aircraft(root, info, id: int, public: Optional[bool] = False) -> Aircraft:
        if not info.context.user_id and not public:
            raise HTTPException(HTTP_401_UNAUTHORIZED)

        return await AircraftQueryResolver().get_one(
            id, user_id=info.context.user_id, organization_ids=info.context.organization_ids, public=public
        )


@strawberry.type
class AircraftMutation:
    @strawberry.mutation
    @error_logging
    @authenticated_user_only()
    async def create_aircraft(root, info, input: CreateAircraftInput) -> Aircraft:
        return await AircraftMutationResolver().create_new(input, info.context.user_id)

    @strawberry.mutation
    @error_logging
    @authenticated_user_only()
    async def edit_aircraft(root, info, id: int, input: EditAircraftInput) -> Aircraft:
        return await AircraftMutationResolver().edit(id, user_id=info.context.user_id, data=input)

    @strawberry.mutation
    @authenticated_user_only()
    async def delete_aircraft(self, info, id: int) -> Aircraft:
        return await AircraftMutationResolver().delete(info.context.user_id, id)
