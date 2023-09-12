from collections import defaultdict
from typing import List, Literal
from sqlalchemy import select
from strawberry.dataloader import DataLoader
from database import async_session
from database.models import Photo


class PhotoDataloader:

    def __init__(self, relationship_column: Literal['flight_id', 'point_of_interest_id']) -> None:
        super().__init__()
        self.relationship_column = relationship_column

    async def load_collection(self, ids: List[int]):
        async with async_session() as session:
            models = (await session.scalars(
                select(Photo)
                .filter(getattr(Photo, self.relationship_column).in_(ids))
                .order_by(Photo.exposed_at)
            )).all()
            photos_by_relationship_id = defaultdict(list)
            for photo in models:
                photos_by_relationship_id[getattr(photo, self.relationship_column)].append(photo)

            return [photos_by_relationship_id[id_] for id_ in ids]


async def flight_cover_photo_load(ids: List[int]):
    async with async_session() as session:
        models = (
            await session.scalars(
                select(Photo)
                .filter(Photo.is_flight_cover.is_(True))
                .filter(Photo.flight_id.in_(ids)))
        ).all()
        photos = {p.flight_id: p for p in models}
        return [photos.get(id_) for id_ in ids]


cover_photo_loader = DataLoader(load_fn=flight_cover_photo_load, cache=False)
photos_dataloader = DataLoader(load_fn=PhotoDataloader("flight_id").load_collection, cache=False)
poi_photos_dataloader = DataLoader(load_fn=PhotoDataloader("point_of_interest_id").load_collection, cache=False)
