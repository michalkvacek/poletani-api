from typing import List, Optional
import strawberry
from database import models
from decorators.endpoints import authenticated_user_only
from dependencies.db import get_session
from graphql_schema.entities.helpers.combobox import handle_combobox_save
from graphql_schema.sqlalchemy_to_strawberry_type import strawberry_sqlalchemy_input
from graphql_schema.entities.types.types import PointOfInterest
from .resolvers.base import get_base_resolver, get_list, get_one
from graphql_schema.entities.types.mutation_input import ComboboxInput


@strawberry.type
class PointOfInterestQueries:
    @strawberry.field()
    @authenticated_user_only()
    async def points_of_interest(root, info) -> List[PointOfInterest]:
        query = get_base_resolver(models.PointOfInterest, user_id=info.context.user_id)
        return await get_list(models.PointOfInterest, query)

    @strawberry.field()
    @authenticated_user_only()
    async def point_of_interest(root, info, id: int) -> PointOfInterest:
        query = get_base_resolver(models.PointOfInterest, user_id=info.context.user_id, object_id=id)
        return await get_one(models.PointOfInterest, query)


@strawberry.type
class CreatePointOfInterestMutation:
    @strawberry_sqlalchemy_input(models.PointOfInterest, exclude_fields=['id', 'type_id'])
    class CreatePointOfInterestInput:
        type: Optional[ComboboxInput] = None

    @strawberry.mutation
    @authenticated_user_only()
    async def create_point_of_interest(root, info, input: CreatePointOfInterestInput) -> PointOfInterest:
        input_data = input.to_dict()

        async with get_session() as db:
            if input.type:
                input_data['type_id'] = await handle_combobox_save(
                    db, models.PointOfInterestType, input.type, info.context.user_id
                )

            poi = await models.PointOfInterest.create(db, data=dict(**input_data, created_by_id=info.context.user_id))
            return PointOfInterest(**poi.as_dict())


@strawberry.type
class EditPointOfInterestMutation:
    @strawberry_sqlalchemy_input(models.PointOfInterest, exclude_fields=['id', 'type_id'])
    class EditPointOfInterestInput:
        type: Optional[ComboboxInput] = None

    @strawberry.mutation
    @authenticated_user_only()
    async def edit_point_of_interest(root, info, id: int, input: EditPointOfInterestInput) -> PointOfInterest:
        input_data = input.to_dict()

        query = get_base_resolver(
            models.PointOfInterest, user_id=info.context.user_id, object_id=id, include_public=False
        )

        async with get_session() as db:
            if input.type is not None:
                input_data['type_id'] = await handle_combobox_save(
                    db, models.PointOfInterestType, input.type, info.context.user_id
                )

            poi = (await db.scalars(query)).one()
            updated_poi = await models.PointOfInterest.update(db, obj=poi, data=input_data)
            return PointOfInterest(**updated_poi.as_dict())


@strawberry.type
class DeletePointOfInterestMutation:

    @strawberry.mutation
    @authenticated_user_only()
    async def delete_point_of_interest(self, info, id: int) -> PointOfInterest:
        query = get_base_resolver(
            models.PointOfInterest, user_id=info.context.user_id, object_id=id, include_public=False
        )

        async with get_session() as db:
            poi = (await db.scalars(query)).one()

            updated_poi = await models.PointOfInterest.update(db, obj=poi, data=dict(deleted=True))
            return PointOfInterest(**updated_poi.as_dict())
