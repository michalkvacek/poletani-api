from typing import List
from sqlalchemy import select
from strawberry.dataloader import DataLoader
from database import async_session
from database.models import Aircraft


async def load(ids: List[int]):
    async with async_session() as session:
        models = (await session.scalars(select(Aircraft).filter(Aircraft.id.in_(ids)))).all()

        models_by_id = {model.id: model for model in models}
        return [models_by_id.get(id_) for id_ in ids]


aircraft_dataloader = DataLoader(load_fn=load)
