from collections import defaultdict
from typing import List
from sqlalchemy import select
from strawberry.dataloader import DataLoader
from database import async_session
from database.models import Event


async def load(ids: List[int]):
    async with async_session() as session:
        models = (await session.scalars(
            select(Event)
            .filter(Event.id.in_(ids))
        )).all()

        events_by_id = {}
        for event in models:
            events_by_id[event.id] = event

        return [events_by_id.get(id_) for id_ in ids]


event_dataloader = DataLoader(load_fn=load, cache=False)
