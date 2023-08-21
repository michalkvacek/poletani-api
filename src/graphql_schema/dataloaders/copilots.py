from collections import defaultdict
from typing import List
from sqlalchemy import select
from strawberry.dataloader import DataLoader
from database import async_session
from database.models import Copilot, Flight


async def load(ids: List[int]):
    async with async_session() as session:
        models = (await session.execute(
            select(Copilot, Flight.id)
            .join(Copilot.flights)
            .filter(Flight.id.in_(ids))
        )).all()

        copilots_by_flight_id = defaultdict(list)
        for copilot, flight_id in models:
            copilots_by_flight_id[flight_id].append(copilot)

        return [copilots_by_flight_id[id_] for id_ in ids]


flight_copilots_dataloader = DataLoader(load_fn=load, cache=False)
