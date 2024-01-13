from typing import Optional
import strawberry
from decorators.endpoints import authenticated_user_only, allow_public
from decorators.error_logging import error_logging
from .helpers.pagination import get_pagination_window, PaginationWindow
from .resolvers.aircraft import AircraftMutationResolver, AircraftQueryResolver
from graphql_schema.entities.types.mutation_input import CreateAircraftInput, EditAircraftInput
from graphql_schema.entities.types.types import Aircraft


@strawberry.type
class AircraftQueries:
    @strawberry.field()
    @error_logging
    @authenticated_user_only()
    async def aircrafts(root, info, limit: int, offset: int = 0) -> PaginationWindow[Aircraft]:
        query = AircraftQueryResolver().get_query(
            info.context.user_id,
            organization_ids=info.context.organization_ids
        )

        return await get_pagination_window(
            query=query,
            item_type=Aircraft,
            limit=limit,
            offset=offset
        )

    @strawberry.field()
    @error_logging
    @allow_public
    async def aircraft(
            root, info,
            id: Optional[int] = None,
            call_sign: Optional[str] = None,
            public: Optional[bool] = False
    ) -> Aircraft:
        filter_params = {}

        if id:
            filter_params['object_id'] = id

        if call_sign:
            filter_params['call_sign'] = call_sign

        return await AircraftQueryResolver().get_one(
            user_id=info.context.user_id,
            organization_ids=info.context.organization_ids,
            only_public=public,
            **filter_params
        )


@strawberry.type
class AircraftMutation:
    @strawberry.mutation
    @error_logging
    @authenticated_user_only()
    async def create_aircraft(root, info, input: CreateAircraftInput) -> Aircraft:
        return await AircraftMutationResolver().create(info.context, input)

    @strawberry.mutation
    @error_logging
    @authenticated_user_only()
    async def edit_aircraft(root, info, id: int, input: EditAircraftInput) -> Aircraft:
        return await AircraftMutationResolver().update(id, user_id=info.context.user_id, data=input)

    @strawberry.mutation
    @authenticated_user_only()
    async def delete_aircraft(self, info, id: int) -> Aircraft:
        return await AircraftMutationResolver().delete(info.context.user_id, id)
