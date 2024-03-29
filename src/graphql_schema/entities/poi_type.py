from typing import List
import strawberry
from database import models
from decorators.endpoints import authenticated_user_only
from decorators.error_logging import error_logging
from graphql_schema.entities.resolvers.base import BaseQueryResolver
from graphql_schema.entities.types.types import PointOfInterestType


@strawberry.type
class PointOfInterestTypeQueries:

    @strawberry.field()
    @error_logging
    @authenticated_user_only()
    async def point_of_interest_types(root, info) -> List[PointOfInterestType]:
        return await BaseQueryResolver(PointOfInterestType, models.PointOfInterestType).get_list(info.context.user_id)

    @strawberry.field()
    @error_logging
    @authenticated_user_only()
    async def point_of_interest_type(root, info, id: int) -> PointOfInterestType:
        return await BaseQueryResolver(PointOfInterestType, models.PointOfInterestType).get_one(
            object_id=id,
            user_id=info.context.user_id
        )

#
# @strawberry.type
# class CreatePointOfInterestMutation:
#     @strawberry_sqlalchemy_input(models.PointOfInterest, exclude_fields=['id', 'type_id'])
#     class CreatePointOfInterestInput:
#         type: # Optional[ComboboxInput] = None
#
#     @strawberry.mutation
#     @authenticated_user_only()
#     async def create_point_of_interest(root, info, input: CreatePointOfInterestInput) -> PointOfInterest:
#         input_data = input.to_dict()
#
#         input_data['type_id'] = await handle_combobox_save(
#             info.context.db,
#             models.PointOfInterestType,
#             input.type,
#             info.context.user_id
#         )
#
#         return await models.PointOfInterest.create(
#             info.context.db,
#             data=dict(
#                 **input_data,
#                 created_by_id=info.context.user_id,
#             )
#         )
#
#
# @strawberry.type
# class EditPointOfInterestMutation:
#     @strawberry_sqlalchemy_input(models.PointOfInterest, exclude_fields=['id', 'type_id'])
#     class EditPointOfInterestInput:
#         type: Optional[ComboboxInput] = None
#
#     @strawberry.mutation
#     @authenticated_user_only()
#     async def edit_point_of_interest(root, info, id: int, input: EditPointOfInterestInput) -> PointOfInterest:
#         # TODO: kontrola organizace
#         input_data = input.to_dict()
#
#         if 'type' in input:
#             input_data['type_id'] = await handle_combobox_save(
#                 info.context.db,
#                 models.PointOfInterestType,
#                 input.type,
#                 info.context.user_id
#             )
#
#         poi = (
#             await info.context.db.scalars(
#                 get_base_query(info.context.user_id, only_my=True)
#                 .filter(models.PointOfInterest.id == id))
#         ).one()
#         return await models.PointOfInterest.update(info.context.db, obj=poi, data=input_data)
#
#
# @strawberry.type
# class DeletePointOfInterestMutation:
#
#     @strawberry.mutation
#     @authenticated_user_only()
#     async def delete_point_of_interest(self, info, id: int) -> PointOfInterest:
#         poi = get_base_query(info.context.user_id, only_my=True).filter(models.PointOfInterest.id == id).one()
#
#         return await models.PointOfInterest.update(info.context.db, obj=poi, data=dict(deleted=True))
