from datetime import timedelta
from typing import List, Optional, Annotated, TYPE_CHECKING, Tuple
import strawberry
from fastapi import HTTPException
from sqlalchemy import select, insert, delete
from starlette.status import HTTP_401_UNAUTHORIZED
from strawberry.file_uploads import Upload
from database import models
from database.models import flight_has_copilot
from decorators.endpoints import authenticated_user_only
from decorators.error_logging import error_logging
from graphql_schema.dataloaders.aircraft import aircraft_dataloader
from graphql_schema.dataloaders.airport import airport_dataloader
from graphql_schema.dataloaders.copilots import flight_copilots_dataloader
from graphql_schema.dataloaders.photos import photos_dataloader, cover_photo_loader
from graphql_schema.dataloaders.poi import flight_track_dataloader, poi_dataloader
from graphql_schema.dataloaders.weather import airport_weather_info_loader
from graphql_schema.entities.aircraft import Aircraft
from graphql_schema.entities.airport import Airport
from graphql_schema.entities.photo import Photo
from graphql_schema.entities.poi import PointOfInterest
from graphql_schema.sqlalchemy_to_strawberry_type import strawberry_sqlalchemy_type, strawberry_sqlalchemy_input
from upload_utils import get_public_url
from .helpers.flight import handle_aircraft_save, handle_track_edit, handle_copilots_edit, handle_weather_info, get_airports, handle_upload_gpx, handle_airport_changed
from ..types import ComboboxInput

if TYPE_CHECKING:
    from .copilot import Copilot


@strawberry_sqlalchemy_type(models.FlightTrack)
class FlightTrack:
    async def load_poi(root):
        return await poi_dataloader.load(root.point_of_interest_id)

    point_of_interest: PointOfInterest = strawberry.field(resolver=load_poi)


@strawberry_sqlalchemy_type(models.WeatherInfo)
class WeatherInfo:
    pass


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

    async def load_photos(root):
        return await photos_dataloader.load(root.id)

    async def load_cover_photo(root):
        return await cover_photo_loader.load(root.id)

    async def load_takeoff_weather_info(root):
        return await airport_weather_info_loader.load(root.takeoff_weather_info_id)

    async def load_landing_weather_info(root):
        return await airport_weather_info_loader.load(root.landing_weather_info_id)

    def duration_min_calculated(root):
        if root.duration_total:
            return root.duration_total

        if root.takeoff_datetime and root.landing_datetime:
            diff: timedelta = root.landing_datetime - root.takeoff_datetime
            return diff.seconds / 60

        return 0

    def load_gpx_track_url(root):
        if not root.gpx_track_filename:
            return None

        return get_public_url(f"/tracks/{root.gpx_track_filename}")

    @authenticated_user_only(raise_when_unauthorized=False, return_value_unauthorized=[])
    async def load_copilots(root):
        return await flight_copilots_dataloader.load(root.id)

    duration_min_calculated: int = strawberry.field(resolver=duration_min_calculated)
    copilots: Optional[List[Annotated["Copilot", strawberry.lazy(".copilot")]]] = strawberry.field(resolver=load_copilots)
    aircraft: Aircraft = strawberry.field(resolver=load_aircraft)
    takeoff_airport: Airport = strawberry.field(resolver=load_takeoff_airport)
    landing_airport: Airport = strawberry.field(resolver=load_landing_airport)
    cover_photo: Optional[Photo] = strawberry.field(resolver=load_cover_photo)
    track: List[FlightTrack] = strawberry.field(resolver=load_track)
    takeoff_weather_info: Optional[WeatherInfo] = strawberry.field(resolver=load_takeoff_weather_info)
    landing_weather_info: Optional[WeatherInfo] = strawberry.field(resolver=load_landing_weather_info)
    photos: List[Photo] = strawberry.field(resolver=load_photos)
    gpx_track_url: Optional[str] = strawberry.field(resolver=load_gpx_track_url)


def get_base_query(user_id: Optional[int], username: Optional[str] = None, is_auth: bool = False):
    query = (
        select(models.Flight)
        .filter(models.Flight.deleted.is_(False))
        .order_by(models.Flight.id.desc())
    )

    if user_id:
        query = query.filter(models.Flight.created_by_id == user_id)

    if username:
        query = query.join(models.Flight.created_by).filter(models.User.public_username == username)

    if not is_auth:
        query = query.filter(models.Flight.is_public.is_(True))

    return query


@strawberry.type
class FlightQueries:

    @strawberry.field()
    async def flights(root, info, username: Optional[str] = None) -> List[Flight]:
        if not info.context.user_id and not username:
            raise HTTPException(HTTP_401_UNAUTHORIZED, f"user_id={info.context.user_id}, {username=}")

        query = (
            get_base_query(user_id=info.context.user_id, username=username, is_auth=bool(info.context.user_id))
            .order_by(models.Flight.id.desc())
        )
        return (await info.context.db.scalars(query)).all()

    @strawberry.field()
    @error_logging
    async def flight(root, info, id: int, username: Optional[str] = None) -> Flight:
        if not info.context.user_id and not username:
            raise HTTPException(HTTP_401_UNAUTHORIZED)

        query = (
            get_base_query(user_id=info.context.user_id, username=username, is_auth=bool(info.context.user_id))
            .filter(models.Flight.id == id)
        )
        return (await info.context.db.scalars(query)).one()


@strawberry.type
class CreateFlightMutation:
    @strawberry_sqlalchemy_input(models.Flight, exclude_fields=[
        "id", "aircraft_id", "landing_airport_id", "takeoff_airport_id", "weather_info_takeoff_id",
        "weather_info_landing_id", "with_instructor"
    ])
    class CreateFlightInput:
        aircraft: ComboboxInput
        landing_airport: ComboboxInput
        takeoff_airport: ComboboxInput

    @strawberry.mutation
    @authenticated_user_only()
    async def create_flight(self, info, input: CreateFlightInput) -> Flight:
        db = info.context.db
        aircraft_id = await handle_aircraft_save(db, info.context.user_id, input.aircraft)

        data = input.to_dict()
        takeoff_airport, landing_airport = await get_airports(db, input.takeoff_airport.id, input.landing_airport.id)
        weather_takeoff = await handle_weather_info(db, data['takeoff_datetime'], takeoff_airport)
        weather_landing = await handle_weather_info(db, data['landing_datetime'], landing_airport)

        return await models.Flight.create(db, data={
            **data,
            "takeoff_weather_info_id": weather_takeoff.id,
            "landing_weather_info_id": weather_landing.id,
            "takeoff_airport_id": takeoff_airport.id,
            "landing_airport_id": landing_airport.id,
            "aircraft_id": aircraft_id,
            "created_by_id": info.context.user_id
        })


@strawberry.type
class EditFlightMutation:
    @strawberry_sqlalchemy_input(models.Flight, exclude_fields=[
        "id", "aircraft_id", "deleted", "landing_airport_id", "takeoff_airport_id"
        "takeoff_weather_info_id", "landing_weather_info_id", "gpx_track_filename"
    ], all_optional=True)
    class EditFlightInput:
        gpx_track: Optional[Upload] = None  # TODO: poresit validaci uploadovaneho souboru!
        track: Optional[List[ComboboxInput]] = None
        copilots: Optional[List[ComboboxInput]] = None
        aircraft: Optional[ComboboxInput] = None
        landing_airport: Optional[ComboboxInput] = None
        takeoff_airport: Optional[ComboboxInput] = None

    @strawberry.mutation
    @authenticated_user_only()
    async def edit_flight(self, info, id: int, input: EditFlightInput) -> Flight:
        db = info.context.db
        user_id = info.context.user_id

        flight = (await db.scalars(
            get_base_query(user_id=user_id, is_auth=bool(user_id)).filter(models.Flight.id == id)
        )).one()

        takeoff_airport, landing_airport = await get_airports(
            db,
            takeoff_airport_id=input.takeoff_airport.id if input.takeoff_airport else flight.takeoff_airport_id,
            landing_airport_id=input.landing_airport.id if input.landing_airport else flight.landing_airport_id,
        )

        data = input.to_dict()

        if input.gpx_track is not None:
            data['gpx_track_filename'] = await handle_upload_gpx(flight, input.gpx_track)

        if input.takeoff_airport and input.takeoff_airport.id != flight.takeoff_airport_id:
            await handle_airport_changed(
                db,
                flight,
                takeoff_airport,
                type_="takeoff",
                input_datetime=data.get('takeoff_datetime')
            )

        if input.landing_airport and input.landing_airport.id != flight.landing_airport_id:
            await handle_airport_changed(
                db,
                flight,
                landing_airport,
                type_="landing",
                input_datetime=data.get('landing_datetime')
            )

        if input.aircraft is not None:
            data['aircraft_id'] = await handle_aircraft_save(db, user_id, input.aircraft)

        if input.track is not None:
            await handle_track_edit(db=db, flight=flight, track=input.track, user_id=user_id)

        copilots = await handle_copilots_edit(db, input.copilots or [], user_id)
        await db.execute(delete(flight_has_copilot).filter_by(flight_id=flight.id))
        for copilot_id in copilots:
            await db.execute(insert(flight_has_copilot).values(flight_id=flight.id, copilot_id=copilot_id))

        return await models.Flight.update(db, obj=flight, data=data)


@strawberry.type
class DeleteFlightMutation:

    @strawberry.mutation
    @authenticated_user_only()
    async def delete_flight(self, info, id: int) -> Flight:
        flight = (
            (await info.context.db.scalars(
                get_base_query(user_id=info.context.user_id, is_auth=True)
                .filter(models.Flight.id == id))
             )
            .one()
        )
        flight.deleted = True

        return flight
