from typing import List, Optional, Annotated, TYPE_CHECKING, Set
import strawberry
from strawberry.file_uploads import Upload
from database import models
from decorators.endpoints import authenticated_user_only
from dependencies.db import get_session
from graphql_schema.sqlalchemy_to_strawberry_type import strawberry_sqlalchemy_type, strawberry_sqlalchemy_input
from upload_utils import handle_file_upload, delete_file, get_public_url
from graphql_schema.entities.helpers.combobox import handle_combobox_save
from .resolvers.aircraft import get_aircraft_resolver
from .resolvers.base import get_list, get_one
from ..dataloaders.flight import flights_by_aircraft_dataloader
from ..dataloaders.organizations import organizations_dataloader
from ..types import ComboboxInput

if TYPE_CHECKING:
    from .flight import Flight
    from .organization import Organization

AIRCRAFT_UPLOAD_DEST_PATH = "/app/uploads/aircrafts/"


@strawberry_sqlalchemy_type(models.Aircraft)
class Aircraft:
    async def load_flights(root):
        return await flights_by_aircraft_dataloader.load(root.id)

    async def load_organization(root):
        return await organizations_dataloader.load(root.organization_id)

    photo_url: Optional[str] = strawberry.field(
        resolver=lambda root: get_public_url(f"aircrafts/{root.photo_filename}") if root.photo_filename else None
    )
    flights: List[Annotated["Flight", strawberry.lazy('.flight')]] = strawberry.field(resolver=load_flights)
    organization: Optional[Annotated["Organization", strawberry.lazy(".organization")]] = strawberry.field(
        resolver=load_organization
    )


@strawberry.type
class AircraftQueries:
    @strawberry.field()
    @authenticated_user_only()
    async def aircrafts(root, info) -> List[Aircraft]:
        query = get_aircraft_resolver(info.context.user_id, info.context.organization_ids)
        return await get_list(models.Aircraft, query)

    @strawberry.field()
    @authenticated_user_only()
    async def aircraft(root, info, id: int) -> Aircraft:
        query = get_aircraft_resolver(info.context.user_id, info.context.organization_ids, id)
        return await get_one(models.Aircraft, query)


@strawberry.type
class CreateAircraftMutation:
    @strawberry_sqlalchemy_input(models.Aircraft, exclude_fields=['id', 'photo_filename'])
    class CreateAircraftInput:
        photo: Optional[Upload]
        organization: Optional[ComboboxInput] = None

    @strawberry.mutation
    @authenticated_user_only()
    async def create_aircraft(root, info, input: CreateAircraftInput) -> Aircraft:
        # TODO: kontrola organizace

        input_data = input.to_dict()
        if input.photo:
            input_data['photo_filename'] = await handle_file_upload(input.photo, AIRCRAFT_UPLOAD_DEST_PATH)

        async with get_session() as db:
            if input.organization:
                input_data['organization_id'] = await handle_combobox_save(
                    db,
                    models.Organization,
                    input=input.organization,
                    user_id=info.context.user_id,
                )

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
        organization: Optional[ComboboxInput] = None

    @strawberry.mutation
    @authenticated_user_only()
    async def edit_aircraft(root, info, id: int, input: EditAircraftInput) -> Aircraft:
        # TODO: kontrola organizace

        update_data = input.to_dict()
        async with get_session() as db:
            if input.organization:
                update_data['organization_id'] = await handle_combobox_save(
                    db,
                    models.Organization,
                    input=input.organization,
                    user_id=info.context.user_id,
                )

            aircraft = (await db.scalars(get_aircraft_resolver(user_id=info.context.user_id, aircraft_id=id))).one()

            if input.photo:
                if aircraft.photo_filename:
                    delete_file(AIRCRAFT_UPLOAD_DEST_PATH + "/" + aircraft.photo_filename, silent=True)
                update_data['photo_filename'] = await handle_file_upload(input.photo, AIRCRAFT_UPLOAD_DEST_PATH)

            aircraft = await models.Aircraft.update(db, obj=aircraft, data=update_data)

            return Aircraft(**aircraft.as_dict())


@strawberry.type
class DeleteAircraftMutation:

    @strawberry.mutation
    @authenticated_user_only()
    async def delete_aircraft(self, info, id: int) -> Aircraft:
        async with get_session() as db:
            aircraft = (await db.scalars(get_aircraft_resolver(info.context.user_id, aircraft_id=id))).one()

            aircraft = await models.Aircraft.update(db, obj=aircraft, data=dict(deleted=True))
            return Aircraft(**aircraft.as_dict())
