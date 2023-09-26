import asyncio
from datetime import timedelta, datetime
from typing import List, Optional, Annotated, TYPE_CHECKING
import strawberry
from fastapi import HTTPException
from sqlalchemy import select, insert, delete
from starlette.status import HTTP_401_UNAUTHORIZED
from strawberry.file_uploads import Upload
from background_jobs.elevation import add_terrain_elevation_to_flight
from database import models
from database.models import flight_has_copilot
from decorators.endpoints import authenticated_user_only
from decorators.error_logging import error_logging
from dependencies.db import get_session
from external.gpx_parser import GPXParser
from graphql_schema.entities.aircraft import Aircraft
from graphql_schema.entities.airport import Airport
from graphql_schema.entities.photo import Photo
from graphql_schema.entities.poi import PointOfInterest
from graphql_schema.sqlalchemy_to_strawberry_type import strawberry_sqlalchemy_type, strawberry_sqlalchemy_input
from upload_utils import get_public_url
from .helpers.flight import (
    handle_aircraft_save, handle_track_edit, handle_copilots_edit, handle_weather_info, get_airports,
    handle_upload_gpx, handle_airport_changed, handle_combobox_save
)
from ..dataloaders.multi_models import flight_copilots_dataloader, flight_track_dataloader, photos_dataloader
from ..dataloaders.single_model import (
    poi_dataloader, event_dataloader, aircraft_dataloader, airport_dataloader, cover_photo_loader,
    airport_weather_info_loader
)
from ..types import ComboboxInput

if TYPE_CHECKING:
    from .copilot import Copilot
    from .event import Event


@strawberry_sqlalchemy_type(models.FlightTrack)
class FlightTrack:
    point_of_interest: PointOfInterest = strawberry.field(
        resolver=lambda root: poi_dataloader.load(root.point_of_interest_id)
    )


@strawberry_sqlalchemy_type(models.WeatherInfo)
class WeatherInfo:
    pass


@strawberry.type
class Point:
    lat: float
    lng: float


@strawberry.type
class GPXTrack:
    coordinates: List[Point]
    speed: List[float]
    altitude: List[float]
    magnetic_variation: List[float]
    terrain_elevation: List[float]
    time: List[datetime]
    max_speed: float
    avg_speed: float
    max_altitude: float
    avg_altitude: float


@strawberry_sqlalchemy_type(models.Flight)
class Flight:
    def duration_min_calculated(root):
        if root.duration_total:
            return root.duration_total

        if root.takeoff_datetime and root.landing_datetime:
            diff: timedelta = root.landing_datetime - root.takeoff_datetime
            return diff.seconds / 60

        return 0

    async def load_gpx_track(root):
        if not root.gpx_track_filename:
            return None

        try:
            gpx_parser = GPXParser(f"/app/uploads/tracks/{root.gpx_track_filename}")
        except OSError:
            return None

        return GPXTrack(
            coordinates=[Point(**point) for point in await gpx_parser.get_coordinates()],
            speed=await gpx_parser.get_speed(),
            altitude=await gpx_parser.get_altitude(),
            terrain_elevation=await gpx_parser.get_terrain_elevation(),
            time=await gpx_parser.get_times(),
            max_speed=await gpx_parser.get_max_speed(),
            avg_speed=await gpx_parser.get_avg_speed(),
            max_altitude=await gpx_parser.get_max_altitude(),
            avg_altitude=await gpx_parser.get_avg_altitude(),
            magnetic_variation=await gpx_parser.get_magnetic_variation(),
        )

    def load_gpx_track_url(root):
        if not root.gpx_track_filename:
            return None

        return get_public_url(f"/tracks/{root.gpx_track_filename}")

    @authenticated_user_only(raise_when_unauthorized=False, return_value_unauthorized=[])
    async def load_copilots(root):
        return await flight_copilots_dataloader.load(root.id)

    @authenticated_user_only(raise_when_unauthorized=False, return_value_unauthorized=[])
    async def load_event(root):
        return await event_dataloader.load(root.event_id)

    duration_min_calculated: int = strawberry.field(resolver=duration_min_calculated)
    copilots: Optional[List[Annotated["Copilot", strawberry.lazy(".copilot")]]] = strawberry.field(resolver=load_copilots)  # noqa
    event: Optional[Annotated["Event", strawberry.lazy(".event")]] = strawberry.field(resolver=load_event)
    aircraft: Aircraft = strawberry.field(resolver=lambda root: aircraft_dataloader.load(root.aircraft_id))
    takeoff_airport: Airport = strawberry.field(resolver=lambda root: airport_dataloader.load(root.takeoff_airport_id))
    landing_airport: Airport = strawberry.field(resolver=lambda root: airport_dataloader.load(root.landing_airport_id))
    cover_photo: Optional[Photo] = strawberry.field(resolver=lambda root: cover_photo_loader.load(root.id))
    track: List[FlightTrack] = strawberry.field(resolver=lambda root: flight_track_dataloader.load(root.id))
    takeoff_weather_info: Optional[WeatherInfo] = strawberry.field(
        resolver=lambda root: airport_weather_info_loader.load(root.takeoff_weather_info_id)
    )
    landing_weather_info: Optional[WeatherInfo] = strawberry.field(
        resolver=lambda root: airport_weather_info_loader.load(root.landing_weather_info_id)
    )
    photos: List[Photo] = strawberry.field(resolver=lambda root: photos_dataloader.load(root.id))
    gpx_track_url: Optional[str] = strawberry.field(resolver=load_gpx_track_url)  # TODO: odstranit
    gpx_track: Optional[GPXTrack] = strawberry.field(resolver=load_gpx_track)


def get_base_query(user_id: Optional[int], username: Optional[str] = None, is_auth: bool = False):
    query = (
        select(models.Flight)
        .filter(models.Flight.deleted.is_(False))
        .order_by(models.Flight.takeoff_datetime.desc())
    )

    if user_id:
        query = query.filter(models.Flight.created_by_id == user_id)

    if username:
        query = (
            query
            .join(models.Flight.created_by)
            .filter(models.User.public_username == username)
        )

    if not is_auth:
        query = query.filter(models.Flight.is_public.is_(True))

    return query


@strawberry.type
class FlightQueries:

    @strawberry.field()
    async def flights(root, info, username: Optional[str] = None) -> List[Flight]:
        if not info.context.user_id and not username:
            raise HTTPException(HTTP_401_UNAUTHORIZED)

        query = (
            get_base_query(user_id=info.context.user_id, username=username, is_auth=bool(info.context.user_id))
            .order_by(models.Flight.id.desc())
        )

        async with get_session() as db:
            flights = (await db.scalars(query)).all()
            return [Flight(**f.as_dict()) for f in flights]

    @strawberry.field()
    @error_logging
    async def flight(root, info, id: int, username: Optional[str] = None) -> Flight:
        if not info.context.user_id and not username:
            raise HTTPException(HTTP_401_UNAUTHORIZED)

        query = (
            get_base_query(user_id=info.context.user_id, username=username, is_auth=bool(info.context.user_id))
            .filter(models.Flight.id == id)
        )

        async with get_session() as db:
            flight = (await db.scalars(query)).one()
            return Flight(**flight.as_dict())


@strawberry.type
class CreateFlightMutation:
    @strawberry_sqlalchemy_input(models.Flight, exclude_fields=[
        "id", "aircraft_id", "landing_airport_id", "takeoff_airport_id", "weather_info_takeoff_id",
        "weather_info_landing_id", "with_instructor", "has_terrain_elevation"
    ])
    class CreateFlightInput:
        aircraft: ComboboxInput
        landing_airport: ComboboxInput
        takeoff_airport: ComboboxInput

    @strawberry.mutation
    @authenticated_user_only()
    async def create_flight(self, info, input: CreateFlightInput) -> Flight:
        data = input.to_dict()

        async with get_session() as db:
            takeoff_airport, landing_airport = await get_airports(
                db, input.takeoff_airport, input.landing_airport, info.context.user_id,
            )

            aircraft_id = await handle_aircraft_save(db, info.context.user_id, input.aircraft)
            weather_takeoff, weather_landing = await asyncio.gather(
                handle_weather_info(db, data['takeoff_datetime'], takeoff_airport),
                handle_weather_info(db, data['landing_datetime'], landing_airport)
            )
            await db.flush()

            flight = await models.Flight.create(db, data={
                **data,
                "takeoff_weather_info_id": weather_takeoff.id if weather_takeoff else None,
                "landing_weather_info_id": weather_landing.id if weather_landing else None,
                "takeoff_airport_id": takeoff_airport.id,
                "landing_airport_id": landing_airport.id,
                "has_terrain_elevation": False,
                "aircraft_id": aircraft_id,
                "created_by_id": info.context.user_id
            })
            return Flight(**flight.as_dict())


@strawberry.type
class EditFlightMutation:
    @strawberry_sqlalchemy_input(models.Flight, exclude_fields=[
        "id", "aircraft_id", "deleted", "landing_airport_id", "takeoff_airport_id",
        "takeoff_weather_info_id", "landing_weather_info_id", "gpx_track_filename"
    ], all_optional=True)
    class EditFlightInput:
        gpx_track: Optional[Upload] = None  # TODO: poresit validaci uploadovaneho souboru!
        track: Optional[List[ComboboxInput]] = None
        copilots: Optional[List[ComboboxInput]] = None
        aircraft: Optional[ComboboxInput] = None
        landing_airport: Optional[ComboboxInput] = None
        takeoff_airport: Optional[ComboboxInput] = None
        event: Optional[ComboboxInput] = None

    @strawberry.mutation
    @authenticated_user_only()
    async def edit_flight(self, info, id: int, input: EditFlightInput) -> Flight:
        user_id = info.context.user_id

        async with get_session() as db:

            flight = (await db.scalars(
                get_base_query(user_id=user_id, is_auth=bool(user_id)).filter(models.Flight.id == id)
            )).one()

            data = input.to_dict()

            if input.gpx_track is not None:
                data['gpx_track_filename'] = await handle_upload_gpx(flight, input.gpx_track)
                info.context.background_tasks.add_task(
                    add_terrain_elevation_to_flight, flight=flight.as_dict(), gpx_filename=data['gpx_track_filename']
                )

            if input.takeoff_airport and input.landing_airport:
                takeoff_airport, landing_airport = await get_airports(
                    db, input.takeoff_airport, input.landing_airport, info.context.user_id,
                )

            if (
                    (input.takeoff_airport and input.takeoff_airport.id != flight.takeoff_airport_id) or
                    (data.get('takeoff_datetime') and data.get('takeoff_datetime') != flight.takeoff_datetime)
            ):
                await handle_airport_changed(
                    db,
                    flight,
                    takeoff_airport,
                    type_="takeoff",
                    input_datetime=data.get('takeoff_datetime')
                )

            if (
                    (input.landing_airport and input.landing_airport.id != flight.landing_airport_id) or
                    (data.get('landing_datetime') and data.get('landing_datetime') != flight.takeoff_datetime)
            ):
                await handle_airport_changed(
                    db,
                    flight,
                    landing_airport,
                    type_="landing",
                    input_datetime=data.get('landing_datetime')
                )
            # ///////////// konec editace s letistem - je to hnusny

            if input.aircraft is not None:
                data['aircraft_id'] = await handle_aircraft_save(db, user_id, input.aircraft)

            if input.event is not None:
                data['event_id'] = await handle_combobox_save(
                    db,
                    model=models.Event,
                    input=input.event,
                    extra_data={"description": "", "is_public": False},
                    user_id=info.context.user_id
                )

            if input.track is not None:
                await handle_track_edit(db=db, flight=flight, track=input.track, user_id=user_id)

            copilots = await handle_copilots_edit(db, input.copilots or [], user_id)
            await db.execute(delete(flight_has_copilot).filter_by(flight_id=flight.id))
            for copilot_id in copilots:
                await db.execute(insert(flight_has_copilot).values(flight_id=flight.id, copilot_id=copilot_id))

            updated_flight = await models.Flight.update(db, obj=flight, data=data)

            return Flight(**updated_flight.as_dict())


@strawberry.type
class DeleteFlightMutation:

    @strawberry.mutation
    @authenticated_user_only()
    async def delete_flight(self, info, id: int) -> Flight:
        async with get_session() as db:
            flight = (
                (await db.scalars(
                    get_base_query(user_id=info.context.user_id, is_auth=True)
                    .filter(models.Flight.id == id))
                 )
                .one()
            )

            updated_flight = await models.Flight.update(db, obj=flight, data=dict(deleted=True))

            return Flight(**updated_flight.as_dict())
