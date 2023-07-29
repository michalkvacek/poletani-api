from collections import defaultdict
from typing import List
from sqlalchemy import select
from strawberry.dataloader import DataLoader
from database import async_session
from database.models import Flight


class FlightsLoader:
    def __init__(self, relationship_column: str):
        self.relationship_column = relationship_column

    async def load(self, ids: List[int]):
        async with async_session() as session:
            query = (
                select(Flight)
                .filter(getattr(Flight, self.relationship_column).in_(ids))
            )
            data = (await session.scalars(query)).all()

            result_data = defaultdict(list)
            for poi in data:
                result_data[getattr(poi, self.relationship_column)].append(poi)

            return [result_data[id_] for id_ in ids]

flights_by_copilot_dataloader = DataLoader(load_fn=FlightsLoader("copilot_id").load, cache=False)