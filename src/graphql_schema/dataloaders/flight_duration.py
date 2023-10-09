from typing import List
from sqlalchemy import select, func
from strawberry.dataloader import DataLoader
from database import async_session, models


async def load_flight_durations(ids: List[int]):
    async with async_session() as db:
        flights = (await db.execute(
            select(
                models.Flight.id,
                func.timediff(models.Flight.landing_datetime, models.Flight.takeoff_datetime).label("diff"),
                func.coalesce(func.sum(models.FlightTrack.landing_duration), 0).label("landing_duration")
            ).join(models.Flight.track, isouter=True)
            .group_by(models.Flight.id)
            .filter(models.Flight.id.in_(ids))

        )).all()

        items_by_id = {item.id: item.diff.seconds // 60 - item.landing_duration for item in flights}
        return [items_by_id.get(id_) for id_ in ids]


flight_duration_dataloader = DataLoader(load_fn=load_flight_durations, cache=False)
