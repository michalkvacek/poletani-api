from typing import List, Optional
import strawberry
from strawberry.file_uploads import Upload
from sqlalchemy import select
from database import models
from graphql_schema.sqlalchemy_to_strawberry_type import strawberry_sqlalchemy_type, strawberry_sqlalchemy_input


@strawberry_sqlalchemy_type(models.PointOfInterest)
class PointOfInterest:
    pass


def get_base_query(user_id: int):
    return (
        select(models.PointOfInterest)
        .filter(models.PointOfInterest.created_by_id == user_id)
        .filter(models.PointOfInterest.deleted.is_(False))
    )


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
        # TODO: kontrola organizace

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
    @strawberry_sqlalchemy_input(models.PointOfInterest, exclude_fields=['photo_filename'])
    class EditPointOfInterestInput:
        photo: Optional[Upload]

    @strawberry.mutation
    async def edit_PointOfInterest(root, info, id: int, input: EditPointOfInterestInput) -> PointOfInterest:
        # TODO: kontrola organizace
        # TODO: kontrola opravneni na akci

        poi = await models.PointOfInterest.get_one(info.context.db, id)
        return await models.PointOfInterest.update(info.context.db, obj=poi, data=input.to_dict())


@strawberry.type
class DeletePointOfInterestMutation:

    @strawberry.mutation
    async def delete_point_of_interest(self, info, id: int) -> PointOfInterest:
        # TODO: kontrola opravneni na akci

        return await models.PointOfInterest.update(info.context.db, id=id, data=dict(deleted=True))
