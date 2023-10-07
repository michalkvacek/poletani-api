from __future__ import annotations
from datetime import datetime, timedelta
from typing import Optional, Annotated, List
import strawberry
from sqlalchemy import func, select
from config import API_URL
from database import models
from decorators.endpoints import authenticated_user_only
from dependencies.db import get_session
from external.gpx_parser import GPXParser
from graphql_schema.dataloaders.multi_models import poi_photos_dataloader, flight_by_poi_dataloader, flight_copilots_dataloader, flight_track_dataloader, photos_dataloader, flights_by_aircraft_dataloader, users_in_organization_dataloader, aircrafts_from_organization_dataloader, user_organizations_dataloader, flights_by_event_dataloader, flights_by_copilot_dataloader
from graphql_schema.dataloaders.single_model import poi_dataloader, poi_type_dataloader, event_dataloader, aircraft_dataloader, airport_dataloader, cover_photo_loader, airport_weather_info_loader, organizations_dataloader
from graphql_schema.entities.airport import Airport
from graphql_schema.sqlalchemy_to_strawberry_type import strawberry_sqlalchemy_type
from paths import get_photo_basepath
from upload_utils import file_exists, get_public_url


@strawberry_sqlalchemy_type(models.FlightTrack)
class FlightTrack:
    point_of_interest: Optional[PointOfInterest] = strawberry.field(
        resolver=lambda root: poi_dataloader.load(root.point_of_interest_id)
    )
    airport: Optional[Airport] = strawberry.field(
        resolver=lambda root: airport_dataloader.load(root.airport_id)
    )


@strawberry_sqlalchemy_type(models.PointOfInterestType)
class PointOfInterestType:
    pass


@strawberry_sqlalchemy_type(models.WeatherInfo)
class WeatherInfo:
    pass


@strawberry.type
class Point:
    lat: float
    lng: float


@strawberry_sqlalchemy_type(models.PointOfInterest)
class PointOfInterest:
    type: Optional[PointOfInterestType] = strawberry.field(
        resolver=lambda root: poi_type_dataloader.load(root.type_id)
    )
    photos: List[Annotated["Photo", strawberry.lazy('.photo')]] = strawberry.field(
        resolver=lambda root: poi_photos_dataloader.load(root.id)
    )
    flights: List[Annotated["Flight", strawberry.lazy('.flight')]] = strawberry.field(
        resolver=lambda root: flight_by_poi_dataloader.load(root.id)
    )


@strawberry_sqlalchemy_type(models.Photo)
class Photo:
    def resolve_thumb_url(root):
        thumbnail = get_photo_basepath(root.flight_id) + "/thumbs/" + root.filename
        if not file_exists(thumbnail):
            return get_public_url(f"photos/{root.flight_id}/{root.filename}")

        return get_public_url(f"photos/{root.flight_id}/thumbs/{root.filename}")

    url: str = strawberry.field(resolver=lambda root: get_public_url(f"photos/{root.flight_id}/{root.filename}"))
    thumbnail_url: str = strawberry.field(resolver=resolve_thumb_url)
    point_of_interest: Optional[Annotated["PointOfInterest", strawberry.lazy('.poi')]] = strawberry.field(
        resolver=lambda root: poi_dataloader.load(root.point_of_interest_id)
    )


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
    async def duration_min_calculated(root):
        # TODO: predelat na dataloader, dobu nacitat v DB
        diff: timedelta = root.landing_datetime - root.takeoff_datetime
        total_time_minutes = diff.seconds / 60

        async with get_session() as db:
            landing_durations = (await db.scalars(
                select(func.sum(models.FlightTrack.landing_duration))
                .filter(models.FlightTrack.airport_id.isnot(None))
                .filter(models.FlightTrack.flight_id == root.id)
            )).one() or 0

            print(landing_durations)
        return total_time_minutes - float(landing_durations)

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

    @authenticated_user_only(raise_when_unauthorized=False, return_value_unauthorized=[])
    async def load_copilots(root):
        return await flight_copilots_dataloader.load(root.id)

    @authenticated_user_only(raise_when_unauthorized=False, return_value_unauthorized=[])
    async def load_event(root):
        return await event_dataloader.load(root.event_id)

    duration_min_calculated: int = strawberry.field(resolver=duration_min_calculated)
    copilots: Optional[List[Copilot]] = strawberry.field(resolver=load_copilots)
    event: Optional[Event] = strawberry.field(resolver=load_event)
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
    gpx_track_url: Optional[str] = strawberry.field(
        resolver=lambda root: get_public_url(f"/tracks/{root.gpx_track_filename}") if root.gpx_track_filename else None
    )  # TODO: odstranit
    gpx_track: Optional[GPXTrack] = strawberry.field(resolver=load_gpx_track)


@strawberry_sqlalchemy_type(models.Copilot)
class Copilot:
    flights: List[Annotated["Flight", strawberry.lazy('.flight')]] = strawberry.field(
        resolver=lambda root: flights_by_copilot_dataloader.load(root.id)
    )


@strawberry_sqlalchemy_type(models.Aircraft)
class Aircraft:
    photo_url: Optional[str] = strawberry.field(
        resolver=lambda root: get_public_url(f"aircrafts/{root.photo_filename}") if root.photo_filename else None
    )
    flights: List[Annotated["Flight", strawberry.lazy('.flight')]] = strawberry.field(
        resolver=lambda root: flights_by_aircraft_dataloader.load(root.id)
    )
    organization: Optional[Annotated["Organization", strawberry.lazy(".organization")]] = strawberry.field(
        resolver=lambda root: organizations_dataloader.load(root.organization_id)
    )


@strawberry_sqlalchemy_type(models.Organization)
class Organization:
    users: List[Annotated["User", strawberry.lazy(".user")]] = strawberry.field(
        resolver=lambda root: users_in_organization_dataloader.load(root.id)
    )
    aircrafts: List[Annotated["Aircraft", strawberry.lazy(".aircraft")]] = strawberry.field(
        resolver=lambda root: aircrafts_from_organization_dataloader.load(root.id)
    )


@strawberry_sqlalchemy_type(models.User, exclude_fields=['password_hashed'])
class User:
    async def load_avatar_image_url(root):
        if not root.avatar_image_filename:
            return None

        return get_public_url(f"profile/{root.id}/{root.avatar_image_filename}")

    async def load_title_image_url(root):
        if not root.title_image_filename:
            return f"{API_URL}/static/default-title-image.jpg"

        return get_public_url(f"profile/{root.id}/{root.title_image_filename}")

    avatar_image_url: Optional[str] = strawberry.field(resolver=load_avatar_image_url)
    title_image_url: str = strawberry.field(resolver=load_title_image_url)
    organizations: List[Annotated['Organization', strawberry.lazy(".organization")]] = strawberry.field(
        resolver=lambda root: user_organizations_dataloader.load(root.id)
    )


@strawberry_sqlalchemy_type(models.Event)
class Event:
    flights: List[Annotated["Flight", strawberry.lazy('.flight')]] = strawberry.field(
        resolver=lambda root: flights_by_event_dataloader.load(root.id)
    )
