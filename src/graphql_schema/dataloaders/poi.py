from collections import defaultdict
from typing import List
from sqlalchemy import select
from strawberry.dataloader import DataLoader
from database import async_session
from database.models import PointOfInterest, FlightTrack


async def load_flight_track(flight_ids: List[int]):
    async with async_session() as session:
        query = (
            select(FlightTrack)
            .filter(FlightTrack.flight_id.in_(flight_ids))
            .order_by(FlightTrack.order)
        )
        data = (await session.scalars(query)).all()

        pois_by_flight_id = defaultdict(list)
        for poi in data:
            pois_by_flight_id[poi.flight_id].append(poi)

        return [pois_by_flight_id[id_] for id_ in flight_ids]


flight_track_dataloader = DataLoader(load_fn=load_flight_track, cache=False)


async def load_poi(ids: List[int]):
    async with async_session() as session:
        models = (await session.scalars(select(PointOfInterest).filter(PointOfInterest.id.in_(ids)))).all()

        models_by_id = {model.id: model for model in models}
        return [models_by_id.get(id_) for id_ in ids]


poi_dataloader = DataLoader(load_fn=load_poi, cache=False)
