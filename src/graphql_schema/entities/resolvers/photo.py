from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from database import models
from database.transaction import get_session
from graphql_schema.entities.helpers.combobox import handle_combobox_save
from graphql_schema.entities.resolvers.base import BaseMutationResolver
from graphql_schema.entities.types.mutation_input import EditPhotoInput
from graphql_schema.entities.types.types import Photo


class PhotoMutationResolver(BaseMutationResolver):
    def __init__(self):
        super().__init__(Photo, models.Photo)

    async def reset_flight_cover(self, db: AsyncSession, flight_id: int, ignored_photo_id: int):
        (await db.execute(
            update(models.Photo)
            .filter(models.Photo.flight_id == flight_id)
            .filter(models.Photo.id != ignored_photo_id).values(is_flight_cover=False))
         )

    async def update(self, id: int, input: EditPhotoInput, user_id: int) -> Photo:
        data = input.to_dict()

        async with get_session() as db:
            photo = await self._get_one(db, id, created_by_id=user_id)
            if input.point_of_interest:
                data['point_of_interest_id'] = await handle_combobox_save(
                    db,
                    models.PointOfInterest,
                    input.point_of_interest,
                    user_id,
                    extra_data={"description": ""}
                )

            if input.is_flight_cover:
                # reset other covers
                await self.reset_flight_cover(db, photo.flight_id, id)

            return await self._do_update(db, obj=photo, data=data)
