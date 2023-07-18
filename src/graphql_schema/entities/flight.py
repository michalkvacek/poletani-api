from datetime import timedelta
from typing import List, Optional
import strawberry
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from database import models
from graphql_schema.dataloaders import copilots_dataloader
from graphql_schema.dataloaders.aircraft import aircraft_dataloader
from graphql_schema.dataloaders.airport import airport_dataloader
from graphql_schema.dataloaders.photos import photos_dataloader, cover_photo_loader
from graphql_schema.dataloaders.poi import flight_track_dataloader, poi_dataloader
from graphql_schema.entities.aircraft import Aircraft
from graphql_schema.entities.airport import Airport
from graphql_schema.entities.copilot import CopilotType
from graphql_schema.entities.photo import Photo
from graphql_schema.entities.poi import PointOfInterest
from graphql_schema.sqlalchemy_to_strawberry_type import strawberry_sqlalchemy_type, strawberry_sqlalchemy_input


# Bude se hodit: https://strawberry.rocks/docs/types/lazy


@strawberry.input()
class PointOfInterestInput:
    id: Optional[int] = None
    name: str


@strawberry.input()
class CopilotInput:
    id: Optional[int] = None
    name: str


@strawberry_sqlalchemy_type(models.FlightTrack)
class FlightTrack:
    async def load_poi(root):
        return await poi_dataloader.load(root.point_of_interest_id)

    point_of_interest: PointOfInterest = strawberry.field(resolver=load_poi)


@strawberry_sqlalchemy_type(models.Flight)
class Flight:
    async def load_takeoff_airport(root):
        return await airport_dataloader.load(root.takeoff_airport_id)

    async def load_track(root):
        return await flight_track_dataloader.load(root.id)

    async def load_landing_airport(root):
        return await airport_dataloader.load(root.landing_airport_id)

    async def load_aircraft(root):
        return await aircraft_dataloader.load(root.aircraft_id)

    async def load_copilot(root):
        return await copilots_dataloader.load(root.copilot_id)

    async def load_photos(root):
        return await photos_dataloader.load(root.id)

    async def load_cover_photo(root):
        return await cover_photo_loader.load(root.id)

    def duration_min_calculated(root):
        if root.duration_total:
            return root.duration_total

        if root.takeoff_datetime and root.landing_datetime:
            diff: timedelta = root.landing_datetime - root.takeoff_datetime
            return diff.seconds / 60

        return 0

    duration_min_calculated: int = strawberry.field(resolver=duration_min_calculated)
    copilot: Optional[CopilotType] = strawberry.field(resolver=load_copilot)
    aircraft: Aircraft = strawberry.field(resolver=load_aircraft)
    takeoff_airport: Airport = strawberry.field(resolver=load_takeoff_airport)
    landing_airport: Airport = strawberry.field(resolver=load_landing_airport)
    cover_photo: Optional[Photo] = strawberry.field(resolver=load_cover_photo)
    track: List[FlightTrack] = strawberry.field(resolver=load_track)

    photos: List[Photo] = strawberry.field(resolver=load_photos)


def get_base_query(user_id: int):
    return (
        select(models.Flight)
        .filter(models.Flight.created_by_id == user_id)
        .order_by(models.Flight.id.desc())
    )


@strawberry.type
class FlightQueries:
    @strawberry.input
    class FlightFilters:
        takeoff: Optional[int]

    @strawberry.field
    async def flights(root, info, filters: Optional[FlightFilters] = None) -> List[Flight]:
        query = get_base_query(info.context.user_id).order_by(models.Flight.id.desc())

        return (await info.context.db.scalars(query)).all()

    @strawberry.field
    async def flight(root, info, id: int) -> Flight:
        query = (
            get_base_query(info.context.user_id)
            .filter(models.Flight.id == id)
            .filter(models.Flight.deleted.is_(False))
        )
        return (await info.context.db.scalars(query)).one()


@strawberry.type
class CreateFlightMutation:
    @strawberry_sqlalchemy_input(models.Flight, exclude_fields=["id"])
    class CreateFlightInput:
        pass

    @strawberry.mutation
    async def create_flight(self, info, input: CreateFlightInput) -> Flight:
        return await models.Flight.create(info.context.db, data={
            **input.to_dict(),
            "created_by_id": info.context.user_id
        })


async def handle_track_edit(db: AsyncSession, flight: models.Flight, track: List[PointOfInterestInput], user_id: int):
    await db.execute(delete(models.FlightTrack).filter(models.FlightTrack.flight_id == flight.id))

    existing_poi_ids = [i.id for i in track if i.id]
    poi_query = (
        select(models.PointOfInterest)
        .filter(models.PointOfInterest.created_by_id == user_id)
        .filter(models.PointOfInterest.id.in_(existing_poi_ids))
    )
    pois = (await db.scalars(poi_query)).all()
    poi_map = {poi.id: poi for poi in pois}

    order = 0
    for item in track:
        poi_object = None
        if item.id:
            poi_object = poi_map.get(item.id)

        if not poi_object:
            poi_object = await models.PointOfInterest.create(db, data=dict(created_by_id=user_id, name=item.name))
            await db.flush()

        await models.FlightTrack.create(
            db,
            data={
                "flight_id": flight.id,
                "point_of_interest_id": poi_object.id,
                "order": order
            }
        )
        order += 1


async def handle_copilot_edit(db: AsyncSession, copilot: CopilotInput, user_id: int) -> int:
    if copilot.id:
        return copilot.id
    else:
        copilot = await models.Copilot.create(
            db,
            data={
                "name": copilot.name,
                "created_by_id": user_id,
            }
        )
        await db.flush()
        return copilot.id


@strawberry.type
class EditFlightMutation:
    @strawberry_sqlalchemy_input(models.Flight, exclude_fields=["id", "copilot_id"], all_optional=True)
    class EditFlightInput:
        track: Optional[List[PointOfInterestInput]] = None
        copilot: Optional[CopilotInput] = None

    @strawberry.mutation
    async def edit_flight(self, info, id: int, input: EditFlightInput) -> Flight:
        flight = await models.Flight.update(info.context.db, id=id, data=input.to_dict())

        if input.track is not None:
            await handle_track_edit(db=info.context.db, flight=flight, track=input.track, user_id=info.context.user_id)

        if flight.solo:
            flight.copilot_id = None
        elif input.copilot is not None:
            flight.copilot_id = await handle_copilot_edit(info.context.db, input.copilot, info.context.user_id)

        return flight
