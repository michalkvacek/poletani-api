from typing import List, Annotated, TYPE_CHECKING
import strawberry
from sqlalchemy import select, or_, delete
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.exc import IntegrityError

from database import models
from decorators.endpoints import authenticated_user_only
from dependencies.db import get_session
from graphql_schema.sqlalchemy_to_strawberry_type import strawberry_sqlalchemy_type, strawberry_sqlalchemy_input
from ..dataloaders.aircraft import aircrafts_from_organization_dataloader
from ..dataloaders.users import users_in_organization_dataloader

if TYPE_CHECKING:
    from .user import User
    from .aircraft import Aircraft


@strawberry_sqlalchemy_type(models.Organization)
class Organization:

    async def load_users(self):
        return await users_in_organization_dataloader.load(self.id)

    async def load_aircrafts(self):
        return await aircrafts_from_organization_dataloader.load(self.id)

    users: List[Annotated["User", strawberry.lazy(".user")]] = strawberry.field(resolver=load_users)
    aircrafts: List[Annotated["Aircraft", strawberry.lazy(".aircraft")]] = strawberry.field(resolver=load_aircrafts)


def get_base_query():
    return (
        select(models.Organization)
        .filter(models.Organization.deleted.is_(False))
        .order_by(models.Organization.name)
    )


@strawberry.type
class OrganizationQueries:
    @strawberry.field()
    @authenticated_user_only()
    async def organizations(root, info) -> List[Organization]:
        async with get_session() as db:
            organizations = (await db.scalars(get_base_query())).all()

            return [Organization(**c.as_dict()) for c in organizations]

    @strawberry.field()
    @authenticated_user_only()
    async def organization(root, info, id: int) -> Organization:
        async with get_session() as db:
            organization = (await db.scalars(
                get_base_query()
                .filter(models.Organization.id == id)
            )).one()
            return Organization(**organization.as_dict())


@strawberry.type
class CreateOrganizationMutation:
    @strawberry_sqlalchemy_input(model=models.Organization, exclude_fields=["id"])
    class CreateOrganizationInput:
        pass

    @strawberry.mutation
    @authenticated_user_only()
    async def create_organization(root, info, input: CreateOrganizationInput) -> Organization:
        input_data = input.to_dict()
        async with get_session() as db:
            organization = await models.Organization.create(
                db,
                data=dict(
                    **input_data,
                    created_by_id=info.context.user_id,
                )
            )

            return Organization(**organization.as_dict())


@strawberry.type
class OrganizationUserMutation:

    @strawberry.mutation
    @authenticated_user_only()
    async def add_to_organization(root, info, organization_id: int) -> Organization:
        async with get_session() as db:
            organization = (await db.scalars(get_base_query().filter(models.Organization.id == organization_id))).one()

            try:
                await db.execute(
                    insert(models.user_is_in_organization).values(
                        user_id=info.context.user_id,
                        organization_id=organization_id
                    )
                )
            except IntegrityError:
                print("jiz existuje")
                pass

            return Organization(**organization.as_dict())

    @strawberry.mutation
    @authenticated_user_only()
    async def remove_from_organization(root, info, organization_id: int) -> Organization:
        async with get_session() as db:
            organization = (await db.scalars(get_base_query().filter(models.Organization.id == organization_id))).one()

            await db.execute(
                delete(models.user_is_in_organization).filter_by(
                    user_id=info.context.user_id,
                    organization_id=organization_id
                )
            )

            return Organization(**organization.as_dict())



@strawberry.type
class EditOrganizationMutation:
    @strawberry_sqlalchemy_input(model=models.Organization, exclude_fields=["id"])
    class EditOrganizationInput:
        pass

    @strawberry.mutation
    @authenticated_user_only()
    async def edit_organization(root, info, id: int, input: EditOrganizationInput) -> Organization:
        async with get_session() as db:
            organization = (await db.scalars(
                get_base_query()
                .filter(models.Organization.created_by_id == info.context.user_id)
                .filter(models.Organization.id == id)
            )).one()

            updated_organization = await models.Organization.update(db, obj=organization, data=input.to_dict())
            return Organization(**updated_organization.as_dict())