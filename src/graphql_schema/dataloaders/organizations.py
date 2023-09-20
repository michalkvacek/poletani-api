from collections import defaultdict
from typing import List
from sqlalchemy import select
from strawberry.dataloader import DataLoader
from database import async_session
from database.models import Organization, Flight, user_is_in_organization


async def load(ids: List[int]):
    async with async_session() as session:
        models = (await session.scalars(
            select(Organization)
            .filter(Organization.id.in_(ids))
        )).all()

        organizations_by_id = {}
        for organization in models:
            organizations_by_id[organization.id] = organization

        return [organizations_by_id.get(id_) for id_ in ids]


async def load_organizations(ids: List[int]):
    async with async_session() as session:
        models = (await session.execute(
            select(Organization, user_is_in_organization.c.user_id)
            .join(user_is_in_organization)
            .filter(user_is_in_organization.c.user_id.in_(ids))
        )).all()

        organizations_by_user_id = defaultdict(list)
        for organization, user_id in models:
            organizations_by_user_id[user_id].append(organization)
        return [organizations_by_user_id.get(id_, []) for id_ in ids]


organizations_dataloader = DataLoader(load_fn=load, cache=False)

user_organizations_dataloader = DataLoader(load_fn=load_organizations, cache=False)