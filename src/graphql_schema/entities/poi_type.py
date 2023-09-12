from typing import List, Optional
import strawberry
from sqlalchemy import select, or_
from database import models
from decorators.endpoints import authenticated_user_only
from dependencies.db import get_session
from graphql_schema.sqlalchemy_to_strawberry_type import strawberry_sqlalchemy_type
from graphql_schema.types import ComboboxInput


@strawberry_sqlalchemy_type(models.PointOfInterestType)
class PointOfInterestType:
    pass


def get_base_query(user_id: int, only_my: bool = False):
    query = (
        select(models.PointOfInterestType)
        .filter(models.PointOfInterestType.deleted.is_(False))
    )

    if only_my:
        query = query.filter(models.PointOfInterestType.created_by_id == user_id)
    else:
        query = query.filter(or_(
            models.PointOfInterestType.created_by_id == user_id,
            models.PointOfInterestType.is_public.is_(True)
        ))

    return query


@strawberry.type
class PointOfInterestTypeQueries:

    @strawberry.field()
    @authenticated_user_only()
    async def point_of_interest_types(root, info) -> List[PointOfInterestType]:
        query = (
            get_base_query(info.context.user_id, only_my=False)
            .order_by(models.PointOfInterestType.id.desc())
        )

        async with get_session() as db:
            poi_types = (await db.scalars(query)).all()
            return [PointOfInterestType(**poi_type.as_dict()) for poi_type in poi_types]

    @strawberry.field()
    @authenticated_user_only()
    async def point_of_interest_type(root, info, id: int) -> PointOfInterestType:
        query = (
            get_base_query(info.context.user_id)
            .filter(models.PointOfInterestType.id == id)
        )
        async with get_session() as db:
            poi_type = (await db.scalars(query)).one()
            return PointOfInterestType(**poi_type.as_dict())

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
