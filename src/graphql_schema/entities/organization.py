from typing import List, TYPE_CHECKING
import strawberry
from sqlalchemy import delete
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.exc import IntegrityError
from database import models
from decorators.endpoints import authenticated_user_only
from dependencies.db import get_session
from graphql_schema.sqlalchemy_to_strawberry_type import strawberry_sqlalchemy_input
from .resolvers.base import get_base_resolver, get_list, get_one
from graphql_schema.entities.types.types import Organization

if TYPE_CHECKING:
    pass


@strawberry.type
class OrganizationQueries:
    @strawberry.field()
    @authenticated_user_only()
    async def organizations(root, info) -> List[Organization]:
        query = get_base_resolver(models.Organization, order_by=[models.Organization.name])
        return await get_list(models.Organization, query)

    @strawberry.field()
    @authenticated_user_only()
    async def organization(root, info, id: int) -> Organization:
        query = get_base_resolver(models.Organization, object_id=id)
        return await get_one(models.Organization, query)


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
            organization = (await db.scalars(get_base_resolver(models.Organization, object_id=organization_id))).one()

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
            organization = (await db.scalars(get_base_resolver(models.Organization, object_id=organization_id))).one()

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
                get_base_resolver(models.Organization, user_id=info.context.user_id, object_id=id)
            )).one()

            updated_organization = await models.Organization.update(db, obj=organization, data=input.to_dict())
            return Organization(**updated_organization.as_dict())
