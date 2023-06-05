import os
import uuid
from typing import List, Optional
import strawberry
from strawberry.file_uploads import Upload
from sqlalchemy import select
from database import models
from graphql_schema.sqlalchemy_to_strawberry_type import strawberry_sqlalchemy_type, strawberry_sqlalchemy_input


@strawberry_sqlalchemy_type(models.Aircraft)
class Aircraft:
    photo_url: Optional[str] = strawberry.field(
        resolver=lambda root: f"http://localhost:8000/uploads/{root.photo_filename}" if root.photo_filename else None
    )


def get_base_query(user_id: int):
    return (
        select(models.Aircraft)
        .filter(models.Aircraft.created_by_id == user_id)
        .filter(models.Aircraft.deleted.is_(False))
    )


@strawberry.type
class AircraftQueries:

    @strawberry.field
    async def aircrafts(root, info) -> List[Aircraft]:
        query = (
            get_base_query(info.context.user_id)
            .order_by(models.Aircraft.id.desc())
        )

        return (await info.context.db.scalars(query)).all()

    @strawberry.field
    async def aircraft(root, info, id: int) -> Aircraft:
        query = (
            get_base_query(info.context.user_id)
            .filter(models.Aircraft.id == id)
        )
        return (await info.context.db.scalars(query)).one()


def check_directories(path: str):
    if not os.path.isdir(path):
        os.makedirs(path)


async def handle_img_upload(file: Upload, path: str, filename: str):
    check_directories(path)

    content = await file.read()
    image = open(path + "/" + filename, "wb")
    image.write(content)
    image.close()


@strawberry.type
class CreateAircraftMutation:
    @strawberry_sqlalchemy_input(models.Aircraft, exclude_fields=['id', 'photo_filename'])
    class CreateAircraftInput:
        photo: Optional[Upload]

    @strawberry.mutation
    async def create_aircraft(root, info, input: CreateAircraftInput) -> Aircraft:
        # TODO: kontrola organizace

        filename = None
        if input.photo:
            dest_path = "/app/uploads/aircrafts/"
            filename = f"{uuid.uuid4()}-{input.photo.filename}"
            await handle_img_upload(input.photo, dest_path, filename=filename)

        return await models.Aircraft.create(
            info.context.db,
            data=dict(
                name=input.name,
                description=input.description,
                model=input.model,
                manufacturer=input.manufacturer,
                photo_filename=filename,
                organization_id=input.organization_id,
                created_by_id=info.context.user_id,
            )
        )


@strawberry.type
class EditAircraftMutation:
    @strawberry_sqlalchemy_input(models.Aircraft, exclude_fields=['photo_filename'])
    class EditAircraftInput:
        photo: Optional[Upload]

    @strawberry.mutation
    async def edit_aircraft(root, info, id: int, input: EditAircraftInput) -> Aircraft:
        # TODO: kontrola organizace
        # TODO: kontrola opravneni na akci
        return await models.Aircraft.update(
            info.context.db,
            id,
            data=dict(
                name=input.name,
                description=input.description,
                model=input.model,
                manufacturer=input.manufacturer,
                organization_id=input.organization_id,
            )
        )


@strawberry.type
class DeleteAircraftMutation:

    @strawberry.mutation
    async def delete_aircraft(self, info, id: int) -> Aircraft:
        # TODO: kontrola opravneni na akci

        return await models.Aircraft.update(info.context.db, id, data=dict(deleted=True))
