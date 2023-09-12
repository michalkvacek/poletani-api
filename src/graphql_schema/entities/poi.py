from typing import List, Optional, TYPE_CHECKING, Annotated
import strawberry
from sqlalchemy import select, or_
from database import models
from decorators.endpoints import authenticated_user_only
from dependencies.db import get_session
from graphql_schema.dataloaders.flight import flight_by_poi_dataloader
from graphql_schema.dataloaders.photos import poi_photos_dataloader
from graphql_schema.dataloaders.poi import poi_type_dataloader
from graphql_schema.entities.helpers.flight import handle_combobox_save
from graphql_schema.entities.poi_type import PointOfInterestType
from graphql_schema.sqlalchemy_to_strawberry_type import strawberry_sqlalchemy_type, strawberry_sqlalchemy_input
from graphql_schema.types import ComboboxInput

if TYPE_CHECKING:
    from .flight import Flight
    from .photo import Photo


@strawberry_sqlalchemy_type(models.PointOfInterest)
class PointOfInterest:
    async def load_photos(root):
        return await poi_photos_dataloader.load(root.id)

    async def load_type(root):
        return await poi_type_dataloader.load(root.type_id)

    async def load_flights(root):
        return await flight_by_poi_dataloader.load(root.id)

    type: Optional[PointOfInterestType] = strawberry.field(resolver=load_type)
    photos: List[Annotated["Photo", strawberry.lazy('.photo')]] = strawberry.field(resolver=load_photos)
    flights: List[Annotated["Flight", strawberry.lazy('.flight')]] = strawberry.field(resolver=load_flights)


def get_base_query(user_id: int, only_my: bool = False):
    query = (
        select(models.PointOfInterest)
        .filter(models.PointOfInterest.deleted.is_(False))
    )
    if only_my:
        query = query.filter(models.PointOfInterest.created_by_id == user_id)
    else:
        query = query.filter(or_(
            models.PointOfInterest.created_by_id == user_id,
            models.PointOfInterest.is_public.is_(True)
        ))

    return query


@strawberry.type
class PointOfInterestQueries:

    @strawberry.field()
    @authenticated_user_only()
    async def points_of_interest(root, info) -> List[PointOfInterest]:
        query = (
            get_base_query(info.context.user_id)
            .order_by(models.PointOfInterest.id.desc())
        )
        async with get_session() as db:
            pois = (await db.scalars(query)).all()
            return [PointOfInterest(**poi.as_dict()) for poi in pois]

    @strawberry.field()
    @authenticated_user_only()
    async def point_of_interest(root, info, id: int) -> PointOfInterest:
        query = (
            get_base_query(info.context.user_id)
            .filter(models.PointOfInterest.id == id)
        )
        async with get_session() as db:
            poi = (await db.scalars(query)).one()
            return PointOfInterest(**poi.as_dict())


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
        # TODO: kontrola organizace
        input_data = input.to_dict()

        async with get_session() as db:
            if input.type is not None:
                input_data['type_id'] = await handle_combobox_save(
                    db, models.PointOfInterestType, input.type, info.context.user_id
                )

            poi = (
                await db.scalars(
                    get_base_query(info.context.user_id, only_my=True)
                    .filter(models.PointOfInterest.id == id)
                )).one()
            updated_poi = await models.PointOfInterest.update(db, obj=poi, data=input_data)
            return PointOfInterest(**updated_poi.as_dict())


@strawberry.type
class DeletePointOfInterestMutation:

    @strawberry.mutation
    @authenticated_user_only()
    async def delete_point_of_interest(self, info, id: int) -> PointOfInterest:
        async with get_session() as db:
            poi = (await db.scalars(
                get_base_query(info.context.user_id, only_my=True)
                .filter(models.PointOfInterest.id == id)
            )).one()

            updated_poi = await models.PointOfInterest.update(db, obj=poi, data=dict(deleted=True))
            return PointOfInterest(**updated_poi.as_dict())
