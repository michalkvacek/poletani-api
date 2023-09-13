from typing import List, Optional, Annotated, TYPE_CHECKING
import strawberry
from strawberry.file_uploads import Upload
from sqlalchemy import select
from database import models
from decorators.endpoints import authenticated_user_only
from dependencies.db import get_session
from graphql_schema.sqlalchemy_to_strawberry_type import strawberry_sqlalchemy_type, strawberry_sqlalchemy_input
from upload_utils import handle_file_upload, delete_file, get_public_url
from ..dataloaders.flight import flights_by_aircraft_dataloader

if TYPE_CHECKING:
    from .flight import Flight

AIRCRAFT_UPLOAD_DEST_PATH = "/app/uploads/aircrafts/"


@strawberry_sqlalchemy_type(models.Aircraft)
class Aircraft:
    async def load_flights(root):
        return await flights_by_aircraft_dataloader.load(root.id)

    photo_url: Optional[str] = strawberry.field(
        resolver=lambda root: get_public_url(f"aircrafts/{root.photo_filename}") if root.photo_filename else None
    )

    flights: List[Annotated["Flight", strawberry.lazy('.flight')]] = strawberry.field(resolver=load_flights)


def get_base_query(user_id: int):
    return (
        select(models.Aircraft)
        .filter(models.Aircraft.created_by_id == user_id)
        .filter(models.Aircraft.deleted.is_(False))
    )


@strawberry.type
class AircraftQueries:

    @strawberry.field()
    @authenticated_user_only()
    async def aircrafts(root, info) -> List[Aircraft]:
        query = (
            get_base_query(info.context.user_id)
            .order_by(models.Aircraft.id.desc())
        )
        async with get_session() as db:
            aircrafts = (await db.scalars(query)).all()

            return [Aircraft(**a.as_dict()) for a in aircrafts]

    @strawberry.field()
    @authenticated_user_only()
    async def aircraft(root, info, id: int) -> Aircraft:
        query = (
            get_base_query(info.context.user_id)
            .filter(models.Aircraft.id == id)
        )
        async with get_session() as db:
            aircraft = (await db.scalars(query)).one()
            return Aircraft(**aircraft.as_dict())


@strawberry.type
class CreateAircraftMutation:
    @strawberry_sqlalchemy_input(models.Aircraft, exclude_fields=['id', 'photo_filename'])
    class CreateAircraftInput:
        photo: Optional[Upload]

    @strawberry.mutation
    @authenticated_user_only()
    async def create_aircraft(root, info, input: CreateAircraftInput) -> Aircraft:
        # TODO: kontrola organizace

        input_data = input.to_dict()
        if input.photo:
            input_data['photo_filename'] = await handle_file_upload(input.photo, AIRCRAFT_UPLOAD_DEST_PATH)

        async with get_session() as db:
            aircraft = await models.Aircraft.create(
                db,
                data=dict(
                    **input_data,
                    created_by_id=info.context.user_id,
                )
            )

            return Aircraft(**aircraft.as_dict())


@strawberry.type
class EditAircraftMutation:
    @strawberry_sqlalchemy_input(models.Aircraft, exclude_fields=['photo_filename'])
    class EditAircraftInput:
        photo: Optional[Upload]

    @strawberry.mutation
    @authenticated_user_only()
    async def edit_aircraft(root, info, id: int, input: EditAircraftInput) -> Aircraft:
        # TODO: kontrola organizace

        update_data = input.to_dict()
        async with get_session() as db:
            aircraft = (await db.scalars(
                get_base_query(info.context.user_id)
                .filter(models.Aircraft.id == id)
            )).one()

        if input.photo:
            if aircraft.photo_filename:
                delete_file(AIRCRAFT_UPLOAD_DEST_PATH + "/" + aircraft.photo_filename, silent=True)
            update_data['photo_filename'] = await handle_file_upload(input.photo, AIRCRAFT_UPLOAD_DEST_PATH)

        return await models.Aircraft.update(db, obj=aircraft, data=update_data)


@strawberry.type
class DeleteAircraftMutation:

    @strawberry.mutation
    @authenticated_user_only()
    async def delete_aircraft(self, info, id: int) -> Aircraft:
        async with get_session() as db:
            aircraft = (await db.scalars(
                get_base_query(info.context.user_id)
                .filter(models.Aircraft.id == id)
            )).one()

            aircraft = await models.Aircraft.update(db, obj=aircraft, data=dict(deleted=True))
            return Aircraft(**aircraft.as_dict())
