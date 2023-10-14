from typing import List
import strawberry
from database import models
from decorators.endpoints import authenticated_user_only
from database.transaction import get_session
from graphql_schema.entities.helpers.combobox import handle_combobox_save
from graphql_schema.entities.resolvers.base import BaseQueryResolver, BaseMutationResolver
from graphql_schema.entities.types.types import PointOfInterest
from graphql_schema.entities.types.mutation_input import CreatePointOfInterestInput, EditPointOfInterestInput


@strawberry.type
class PointOfInterestQueries:
    @strawberry.field()
    @authenticated_user_only()
    async def points_of_interest(root, info) -> List[PointOfInterest]:
        return await BaseQueryResolver(PointOfInterest, models.PointOfInterest).get_list(info.context.user_id)

    @strawberry.field()
    @authenticated_user_only()
    async def point_of_interest(root, info, id: int) -> PointOfInterest:
        return await BaseQueryResolver(PointOfInterest, models.PointOfInterest).get_one(id, info.context.user_id)


@strawberry.type
class PointOfInterestMutation:
    @strawberry.mutation
    @authenticated_user_only()
    async def create_point_of_interest(root, info, input: CreatePointOfInterestInput) -> PointOfInterest:
        input_data = input.to_dict()

        async with get_session() as db:
            if input.type:
                input_data['type_id'] = await handle_combobox_save(
                    db, models.PointOfInterestType, input.type, info.context.user_id
                )

        return await BaseMutationResolver(PointOfInterest, models.PointOfInterest).create(
            input_data, info.context.user_id
        )

    @strawberry.mutation
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
    @authenticated_user_only()
    async def delete_point_of_interest(self, info, id: int) -> PointOfInterest:
        return await BaseMutationResolver(PointOfInterest, models.PointOfInterest).delete(info.context.user_id, id=id)
