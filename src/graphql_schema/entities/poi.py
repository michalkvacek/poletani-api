from typing import List, Optional
import strawberry
from graphql import GraphQLError

from database import models
from decorators.endpoints import authenticated_user_only, allow_public
from database.transaction import get_session
from decorators.error_logging import error_logging
from graphql_schema.entities.helpers.combobox import handle_combobox_save
from graphql_schema.entities.helpers.detail import get_detail_filters
from graphql_schema.entities.helpers.pagination import get_pagination_window, PaginationWindow
from graphql_schema.entities.resolvers.base import BaseQueryResolver, BaseMutationResolver
from graphql_schema.entities.types.types import PointOfInterest
from graphql_schema.entities.types.mutation_input import CreatePointOfInterestInput, EditPointOfInterestInput

@strawberry.type
class PointOfInterestQueries:
    @strawberry.field()
    @error_logging
    @allow_public
    async def points_of_interest(
            root, info,
            limit: int, offset: int = 0,
            public: bool = False
    ) -> PaginationWindow[PointOfInterest]:
        query = BaseQueryResolver(PointOfInterest, models.PointOfInterest).get_query(
            info.context.user_id, only_public=public
        )
        return await get_pagination_window(
            query=query,
            item_type=PointOfInterest,
            limit=limit,
            offset=offset
        )

    @strawberry.field()
    @allow_public
    async def point_of_interest(
            root, info,
            url_slug: Optional[str] = None,
            id: Optional[int] = None,
            public: bool = False
    ) -> PointOfInterest:
        filter_params = get_detail_filters(id, url_slug)

        return await BaseQueryResolver(PointOfInterest, models.PointOfInterest).get_one(
            user_id=info.context.user_id,
            only_public=public,
            **filter_params
        )


@strawberry.type
class PointOfInterestMutation:
    @strawberry.mutation
    @error_logging
    @authenticated_user_only()
    async def create_point_of_interest(root, info, input: CreatePointOfInterestInput) -> PointOfInterest:
        input_data = input.to_dict()

        async with get_session() as db:
            if input.type:
                input_data['type_id'] = await handle_combobox_save(
                    db, models.PointOfInterestType, input.type, info.context.user_id
                )

            input_data['created_by_id'] = info.context.user_id
            return await BaseMutationResolver(PointOfInterest, models.PointOfInterest)._do_create(
                db, input_data
            )

    @strawberry.mutation
    @error_logging
    @authenticated_user_only()
    async def edit_point_of_interest(root, info, id: int, input: EditPointOfInterestInput) -> PointOfInterest:
        input_data = input.to_dict()

        query = BaseQueryResolver(PointOfInterest, models.PointOfInterest).get_query(
            user_id=info.context.user_id, object_id=id, only_public=False
        )

        async with get_session() as db:
            if input.type is not None:
                input_data['type_id'] = await handle_combobox_save(
                    db, models.PointOfInterestType, input.type, info.context.user_id
                )

            poi = (await db.scalars(query)).one()
            updated_poi = await models.PointOfInterest.update(db, obj=poi, data=input_data)
            return PointOfInterest(**updated_poi.as_dict())

    @strawberry.mutation
    @error_logging
    @authenticated_user_only()
    async def delete_point_of_interest(self, info, id: int) -> PointOfInterest:
        return await BaseMutationResolver(PointOfInterest, models.PointOfInterest).delete(info.context.user_id, id=id)
