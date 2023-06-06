from typing import List
from sqlalchemy import select
from strawberry.dataloader import DataLoader
from database import async_session
from database.models import Airport


async def load(ids: List[int]):
    async with async_session() as session:
        models = (await session.scalars(select(Airport).filter(Airport.id.in_(ids)))).all()

        models_by_id = {model.id: model for model in models}
        return [models_by_id.get(id_) for id_ in ids]


airport_dataloader = DataLoader(load_fn=load)
