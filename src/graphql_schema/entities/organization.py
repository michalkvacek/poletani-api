from typing import List
import strawberry
from sqlalchemy import delete
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.exc import IntegrityError
from database import models
from decorators.endpoints import authenticated_user_only
from database.transaction import get_session
from decorators.error_logging import error_logging
from graphql_schema.entities.resolvers.base import BaseQueryResolver, BaseMutationResolver
from graphql_schema.entities.types.mutation_input import CreateOrganizationInput, EditOrganizationInput
from graphql_schema.entities.types.types import Organization


@strawberry.type
class OrganizationQueries:
    @strawberry.field()
    @error_logging
    @authenticated_user_only()
    async def organizations(root, info) -> List[Organization]:
        return await BaseQueryResolver(Organization, models.Organization).get_list(
            info.context.user_id, order_by=[models.Organization.name]
        )

    @strawberry.field()
    @error_logging
    @authenticated_user_only()
    async def organization(root, info, id: int) -> Organization:
        return await BaseQueryResolver(Organization, models.Organization).get_one(id, info.context.user_id)


@strawberry.type
class OrganizationMutation:

    @strawberry.mutation
    @error_logging
    @authenticated_user_only()
    async def create_organization(root, info, input: CreateOrganizationInput) -> Organization:
        return await BaseMutationResolver(Organization, models.Organization).create(
            data=input.to_dict(),
            user_id=info.context.user_id
        )

    @strawberry.mutation
    @error_logging
    @authenticated_user_only()
    async def edit_organization(root, info, id: int, input: EditOrganizationInput) -> Organization:
        async with get_session() as db:
            organization = (await db.scalars(
                BaseQueryResolver(Organization, models.Organization).get_query(
                    user_id=info.context.user_id, object_id=id
                )
            )).one()

            updated_organization = await models.Organization.update(db, obj=organization, data=input.to_dict())
            return Organization(**updated_organization.as_dict())


@strawberry.type
class OrganizationUserMutation:

    @strawberry.mutation
    @error_logging
    @authenticated_user_only()
    async def add_to_organization(root, info, organization_id: int) -> Organization:
        async with get_session() as db:
            organization = (await db.scalars(
                BaseQueryResolver(Organization, models.Organization).get_query(object_id=organization_id)
            )).one()

            try:
                await db.execute(
                    insert(models.user_is_in_organization).values(
                        user_id=info.context.user_id,
                        organization_id=organization_id
                    )
                )
            except IntegrityError:
                pass

            return Organization(**organization.as_dict())

    @strawberry.mutation
    @error_logging
    @authenticated_user_only()
    async def remove_from_organization(root, info, organization_id: int) -> Organization:
        async with get_session() as db:
            organization = (await db.scalars(
                BaseQueryResolver(Organization, models.Organization).get_query(object_id=organization_id)
            )).one()

            await db.execute(
                delete(models.user_is_in_organization).filter_by(
                    user_id=info.context.user_id,
                    organization_id=organization_id
                )
            )

            return Organization(**organization.as_dict())
