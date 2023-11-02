from typing import List
import strawberry
from decorators.endpoints import authenticated_user_only
from .resolvers.aircraft import AircraftMutationResolver, AircraftQueryResolver
from graphql_schema.entities.types.mutation_input import CreateAircraftInput, EditAircraftInput
from graphql_schema.entities.types.types import Aircraft


@strawberry.type
class AircraftQueries:
    @strawberry.field()
    @authenticated_user_only()
    async def aircrafts(root, info) -> List[Aircraft]:
        return await AircraftQueryResolver().get_list(
            info.context.user_id,
            organization_ids=info.context.organization_ids
        )

    @strawberry.field()
    @authenticated_user_only()
    async def aircraft(root, info, id: int) -> Aircraft:
        return await AircraftQueryResolver().get_one(
            id, user_id=info.context.user_id, organization_ids=info.context.organization_ids
        )


@strawberry.type
class AircraftMutation:
    @strawberry.mutation
    @authenticated_user_only()
    async def create_aircraft(root, info, input: CreateAircraftInput) -> Aircraft:
        return await AircraftMutationResolver().create_new(input, info.context.user_id)

    @strawberry.mutation
    @authenticated_user_only()
    async def edit_aircraft(root, info, id: int, input: EditAircraftInput) -> Aircraft:
        return await AircraftMutationResolver().edit(id, user_id=info.context.user_id, data=input)

    @strawberry.mutation
    @authenticated_user_only()
    async def delete_aircraft(self, info, id: int) -> Aircraft:
        return await AircraftMutationResolver().delete(info.context.user_id, id)
