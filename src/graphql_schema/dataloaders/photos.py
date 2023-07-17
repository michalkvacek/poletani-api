from collections import defaultdict
from typing import List
from sqlalchemy import select
from strawberry.dataloader import DataLoader
from database import async_session
from database.models import Photo


async def load_collection(ids: List[int]):
    async with async_session() as session:
        models = (await session.scalars(select(Photo).filter(Photo.flight_id.in_(ids)))).all()

        photos_by_flight_id = defaultdict(list)
        for photo in models:
            photos_by_flight_id[photo.flight_id].append(photo)

        return [photos_by_flight_id[id_] for id_ in ids]


async def load(ids: List[int]):
    async with async_session() as session:
        models = (
            await session.scalars(
                select(Photo)
                .filter(Photo.is_flight_cover.is_(True))
                .filter(Photo.flight_id.in_(ids)))
        ).all()
        photos = {p.id: p for p in models}
        return [photos.get(id_) for id_ in ids]


photos_dataloader = DataLoader(load_fn=load_collection, cache=False)

cover_photo_loader = DataLoader(load_fn=load, cache=False)
