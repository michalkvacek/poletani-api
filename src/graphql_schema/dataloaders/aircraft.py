from collections import defaultdict
from typing import List, Optional
from sqlalchemy import select
from strawberry.dataloader import DataLoader
from database import async_session
from database.models import Aircraft, Organization


async def load(ids: List[int]):
    async with async_session() as session:
        models = (await session.scalars(select(Aircraft).filter(Aircraft.id.in_(ids)))).all()

        models_by_id = {model.id: model for model in models}
        return [models_by_id.get(id_) for id_ in ids]


class OrganizationLoader:
    def __init__(self, relationship_column, extra_join: Optional[list] = None):
        if extra_join is None:
            extra_join = []

        self.relationship_column = relationship_column
        self.extra_join = extra_join

    async def load(self, ids: List[int]):
        async with async_session() as session:
            rel_column = self.relationship_column
            query = (
                select(Aircraft, rel_column)
                .filter(rel_column.in_(ids))
            )

            for table in self.extra_join:
                query = query.join(table)

            data = (await session.execute(query)).all()

            result_data = defaultdict(list)
            for item, rel_id in data:
                result_data[rel_id].append(item)

            return [result_data[id_] for id_ in ids]


aircrafts_from_organization_dataloader = DataLoader(
    load_fn=OrganizationLoader(Organization.id, extra_join=[Aircraft.organization]).load,
    cache=False
)

aircraft_dataloader = DataLoader(load_fn=load, cache=False)
