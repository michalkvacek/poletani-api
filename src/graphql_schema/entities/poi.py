from typing import List
import strawberry
from sqlalchemy import select, or_
from database import models
from graphql_schema.dataloaders.photos import poi_photos_dataloader
from graphql_schema.entities.photo import Photo
from graphql_schema.sqlalchemy_to_strawberry_type import strawberry_sqlalchemy_type, strawberry_sqlalchemy_input


@strawberry_sqlalchemy_type(models.PointOfInterest)
class PointOfInterest:
    async def load_photos(root):
        return await poi_photos_dataloader.load(root.id)

    photos: List[Photo] = strawberry.field(resolver=load_photos)


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

    @strawberry.field
    async def points_of_interest(root, info) -> List[PointOfInterest]:
        query = (
            get_base_query(info.context.user_id)
            .order_by(models.PointOfInterest.id.desc())
        )

        return (await info.context.db.scalars(query)).all()

    @strawberry.field
    async def point_of_interest(root, info, id: int) -> PointOfInterest:
        query = (
            get_base_query(info.context.user_id)
            .filter(models.PointOfInterest.id == id)
        )
        return (await info.context.db.scalars(query)).one()


@strawberry.type
class CreatePointOfInterestMutation:
    @strawberry_sqlalchemy_input(models.PointOfInterest, exclude_fields=['id'])
    class CreatePointOfInterestInput:
        pass

    @strawberry.mutation
    async def create_point_of_interest(root, info, input: CreatePointOfInterestInput) -> PointOfInterest:
        input_data = input.to_dict()
        return await models.PointOfInterest.create(
            info.context.db,
            data=dict(
                **input_data,
                created_by_id=info.context.user_id,
            )
        )


@strawberry.type
class EditPointOfInterestMutation:
    @strawberry_sqlalchemy_input(models.PointOfInterest, exclude_fields=['id'])
    class EditPointOfInterestInput:
        pass

    @strawberry.mutation
    async def edit_point_of_interest(root, info, id: int, input: EditPointOfInterestInput) -> PointOfInterest:
        # TODO: kontrola organizace
        # TODO: kontrola opravneni na akci

        poi = (await get_base_query(info.context.user_id, only_my=True).filter(models.Photo.id == id)).one()
        return await models.PointOfInterest.update(info.context.db, obj=poi, data=input.to_dict())


@strawberry.type
class DeletePointOfInterestMutation:

    @strawberry.mutation
    async def delete_point_of_interest(self, info, id: int) -> PointOfInterest:
        poi = (await get_base_query(info.context.user_id, only_my=True).filter(models.Photo.id == id)).one()

        return await models.PointOfInterest.update(info.context.db, obj=poi, data=dict(deleted=True))
