from datetime import timedelta
from typing import List, Optional, Annotated, TYPE_CHECKING
import strawberry
from sqlalchemy import select
from strawberry.file_uploads import Upload

from database import models
from graphql_schema.dataloaders import copilots_dataloader
from graphql_schema.dataloaders.aircraft import aircraft_dataloader
from graphql_schema.dataloaders.airport import airport_dataloader
from graphql_schema.dataloaders.photos import photos_dataloader, cover_photo_loader
from graphql_schema.dataloaders.poi import flight_track_dataloader, poi_dataloader
from graphql_schema.entities.aircraft import Aircraft
from graphql_schema.entities.airport import Airport
from graphql_schema.entities.photo import Photo
from graphql_schema.entities.poi import PointOfInterest
from graphql_schema.sqlalchemy_to_strawberry_type import strawberry_sqlalchemy_type, strawberry_sqlalchemy_input
from upload_utils import handle_file_upload, file_exists, delete_file
from .helpers.flight import handle_aircraft_save, handle_track_edit, handle_copilot_edit, handle_weather_info
from ..dataloaders.weather import airport_weather_info_loader
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

    async def load_copilot(root):
        return await copilots_dataloader.load(root.copilot_id)

    async def load_photos(root):
        return await photos_dataloader.load(root.id)

    async def load_cover_photo(root):
        return await cover_photo_loader.load(root.id)

    async def load_takeoff_weather_info(root):
        return await airport_weather_info_loader.load(root.weather_info_takeoff_id)

    async def load_landing_weather_info(root):
        return await airport_weather_info_loader.load(root.weather_info_landing_id)

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

        return f"http://localhost:8000/uploads/tracks/{root.gpx_track_filename}"

    duration_min_calculated: int = strawberry.field(resolver=duration_min_calculated)
    copilot: Optional[Annotated["Copilot", strawberry.lazy(".copilot")]] = strawberry.field(resolver=load_copilot)
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
        query = query.filter(models.Flight.created_by.public_username == username)
        
    if not is_auth:
        query = query.filter(models.Flight.is_public.is_(True))

    return query


@strawberry.type
class FlightQueries:

    @strawberry.field
    async def flights(root, info, username: Optional[str] = None) -> List[Flight]:
        query = (
            get_base_query(user_id=info.context.user_id, username=username, is_auth=bool(info.context.user_id))
            .order_by(models.Flight.id.desc())
        )
        return (await info.context.db.scalars(query)).all()

    @strawberry.field
    async def flight(root, info, id: int, username: Optional[str] = None) -> Flight:
        query = (
            get_base_query(user_id=info.context.user_id, username=username, is_auth=bool(info.context.user_id))
            .filter(models.Flight.id == id)
            .filter(models.Flight.deleted.is_(False))
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
    async def create_flight(self, info, input: CreateFlightInput) -> Flight:
        aircraft_id = await handle_aircraft_save(info.context.db, info.context.user_id, input.aircraft)
        takeoff_airport = (await info.context.db.scalars(select(models.Airport).filter(models.Airport.id == input.takeoff_airport.id))).one()
        if input.takeoff_airport.id == input.landing_airport.id:
            landing_airport = takeoff_airport
        else:
            landing_airport = (await info.context.db.scalars(select(models.Airport).filter(models.Airport.id == input.landing_airport.id))).one()

        weather_takeoff = await handle_weather_info(info.context.db, input.takeoff_datetime, takeoff_airport)
        weather_landing = await handle_weather_info(info.context.db, input.landing_datetime, landing_airport)

        return await models.Flight.create(info.context.db, data={
            **input.to_dict(),
            "weather_info_takeoff_id": weather_takeoff.id,
            "weather_info_landing_id": weather_landing.id,
            "takeoff_airport_id": takeoff_airport.id,
            "landing_airport_id": landing_airport.id,
            "aircraft_id": aircraft_id,
            "created_by_id": info.context.user_id
        })


@strawberry.type
class EditFlightMutation:
    @strawberry_sqlalchemy_input(models.Flight, exclude_fields=[
        "id", "aircraft_id", "copilot_id", "deleted", "landing_airport_id", "takeoff_airport_id",
        "weather_info_takeoff_id", "weather_info_landing_id", "gpx_track_filename"
    ], all_optional=True)
    class EditFlightInput:
        gpx_track: Optional[Upload] = None
        track: Optional[List[ComboboxInput]] = None
        copilot: Optional[ComboboxInput] = None
        aircraft: Optional[ComboboxInput] = None
        landing_airport: Optional[ComboboxInput] = None
        takeoff_airport: Optional[ComboboxInput] = None

    @strawberry.mutation
    async def edit_flight(self, info, id: int, input: EditFlightInput) -> Flight:
        # TODO: umoznit editovat jen vlastni lety!

        flight = (await info.context.db.scalars(
            get_base_query(user_id=info.context.user_id, is_auth=bool(info.context.user_id)).filter(models.Flight.id == id)
        )).one()

        data = input.to_dict()

        if input.gpx_track is not None:
            # TODO: poresit validaci uploadovaneho souboru!
            path = "/app/uploads/tracks"

            if flight.gpx_track_filename and file_exists(path+"/"+flight.gpx_track_filename):
                delete_file(path+"/"+flight.gpx_track_filename)

            data['gpx_track_filename'] = await handle_file_upload(input.gpx_track, path)

        if input.takeoff_airport is not None:
            # TODO: stahnout nove pocasi na novem miste! Stejne tak pri zmene data/casu odletu
            data['takeoff_airport_id'] = input.takeoff_airport.id

        if input.landing_airport is not None:
            # TODO: stahnout nove pocasi na novem miste! Stejne tak pri zmene data/casu priletu
            data['landing_airport_id'] = input.landing_airport.id

        if input.aircraft is not None:
            data['aircraft_id'] = await handle_aircraft_save(info.context.db, info.context.user_id, input.aircraft)

        flight = await models.Flight.update(info.context.db, id=id, data=data)

        if input.track is not None:
            await handle_track_edit(db=info.context.db, flight=flight, track=input.track, user_id=info.context.user_id)

        if input.copilot:
            flight.copilot_id = await handle_copilot_edit(info.context.db, input.copilot, info.context.user_id)
        else:
            flight.copilot_id = None

        return flight


@strawberry.type
class DeleteFlightMutation:

    @strawberry.mutation
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
