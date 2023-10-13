from typing import List
import strawberry
from database import models
from decorators.endpoints import authenticated_user_only
from database.transaction import get_session
from graphql_schema.entities.helpers.combobox import handle_combobox_save
from paths import AIRCRAFT_UPLOAD_DEST_PATH
from utils.file import delete_file
from utils.upload import handle_file_upload
from .resolvers.aircraft import AircraftMutationResolver, AircraftQueryResolver
from graphql_schema.entities.types.mutation_input import CreateAircraftInput, EditAircraftInput
from graphql_schema.entities.types.types import Aircraft


@strawberry.type
class AircraftQueries:
    @strawberry.field()
    @authenticated_user_only()
    async def aircrafts(root, info) -> List[Aircraft]:
        return await AircraftQueryResolver().get_list(
            info.context.user_id,
            organization_ids=info.context.organization_ids
        )

    @strawberry.field()
    @authenticated_user_only()
    async def aircraft(root, info, id: int) -> Aircraft:
        return await AircraftQueryResolver().get_one(
            id, user_id=info.context.user_id, organization_ids=info.context.organization_ids
        )


@strawberry.type
class AircraftMutation:
    @strawberry.mutation
    @authenticated_user_only()
    async def create_aircraft(root, info, input: CreateAircraftInput) -> Aircraft:
        input_data = input.to_dict()
        if input.photo:
            input_data['photo_filename'] = await handle_file_upload(input.photo, AIRCRAFT_UPLOAD_DEST_PATH)

        if input.organization:
            async with get_session() as db:
                input_data['organization_id'] = await handle_combobox_save(
                    db,
                    models.Organization,
                    input=input.organization,
                    user_id=info.context.user_id,
                )

        return await AircraftMutationResolver().create(data=input_data, user_id=info.context.user_id)

    @strawberry.mutation
    @authenticated_user_only()
    async def edit_aircraft(root, info, id: int, input: EditAircraftInput) -> Aircraft:
        update_data = input.to_dict()
        async with get_session() as db:
            if input.organization:
                update_data['organization_id'] = await handle_combobox_save(
                    db,
                    models.Organization,
                    input=input.organization,
                    user_id=info.context.user_id,
                )

            query = AircraftQueryResolver().get_query(
                user_id=info.context.user_id,
                object_id=id,
                organization_ids=info.context.organization_ids
            )
            aircraft = (await db.scalars(query)).one()
            existing_photo_filename = aircraft.photo_filename

        if input.photo:
            if existing_photo_filename:
                delete_file(AIRCRAFT_UPLOAD_DEST_PATH + "/" + existing_photo_filename, silent=True)
            update_data['photo_filename'] = await handle_file_upload(input.photo, AIRCRAFT_UPLOAD_DEST_PATH)

        async with get_session() as db:
            aircraft = await models.Aircraft.update(db, id=id, data=update_data)
            return Aircraft(**aircraft.as_dict())

    @strawberry.mutation
    @authenticated_user_only()
    async def delete_aircraft(self, info, id: int) -> Aircraft:
        return await AircraftMutationResolver().delete(info.context.user_id, id)
