from __future__ import annotations
from datetime import datetime
from typing import Optional, List
import strawberry
from database import models
from decorators.endpoints import authenticated_user_only
from external.gpx_parser import GPXParser
from graphql_schema.dataloaders.flight_duration import flight_duration_dataloader
from graphql_schema.dataloaders.multi_models import (
    poi_photos_dataloader, flight_by_poi_dataloader, flight_copilots_dataloader, flight_track_dataloader,
    photos_dataloader, flights_by_aircraft_dataloader, users_in_organization_dataloader,
    aircrafts_from_organization_dataloader, user_organizations_dataloader, flights_by_event_dataloader,
    flights_by_copilot_dataloader, public_flights_by_event_dataloader, public_flights_by_copilot_dataloader,
    photo_copilots_dataloader, photos_aircraft_dataloader, copilots_in_photo_dataloader
)
from graphql_schema.dataloaders.single_model import (
    poi_dataloader, poi_type_dataloader, event_dataloader, aircraft_dataloader, airport_dataloader,
    airport_weather_info_loader, organizations_dataloader, flight_dataloader, photo_adjustment_dataloader,
    photo_dataloader, user_dataloader
)
from graphql_schema.sqlalchemy_to_strawberry_type import strawberry_sqlalchemy_type
from paths import get_avatar_url, get_title_image_url, get_photo_thumbnail_url, get_photo_url, FLIGHT_GPX_TRACK_PATH


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


@strawberry_sqlalchemy_type(models.Airport)
class Airport:
    pass


@strawberry_sqlalchemy_type(models.FlightTrack)
class FlightTrack:
    point_of_interest: Optional[PointOfInterest] = strawberry.field(
        resolver=lambda root: poi_dataloader.load(root.point_of_interest_id)
    )
    airport: Optional[Airport] = strawberry.field(resolver=lambda root: airport_dataloader.load(root.airport_id))


@strawberry_sqlalchemy_type(models.PointOfInterestType)
class PointOfInterestType:
    pass


@strawberry_sqlalchemy_type(models.WeatherInfo)
class WeatherInfo:
    pass


@strawberry_sqlalchemy_type(models.PhotoAdjustment)
class PhotoAdjustment:
    photo: Photo = strawberry.field(resolver=lambda root: photo_dataloader.load(root.photo_id))


@strawberry_sqlalchemy_type(models.PointOfInterest)
class PointOfInterest:
    type: Optional[PointOfInterestType] = strawberry.field(resolver=lambda root: poi_type_dataloader.load(root.type_id))
    photos: List[Photo] = strawberry.field(resolver=lambda root: poi_photos_dataloader.load(root.id))
    flights: List[Flight] = strawberry.field(resolver=lambda root: flight_by_poi_dataloader.load(root.id))
    title_photo: Optional[Photo] = strawberry.field(resolver=lambda root: photo_dataloader.load(root.title_photo_id))


@strawberry_sqlalchemy_type(models.Photo)
class Photo:
    url: str = strawberry.field(resolver=get_photo_url)
    thumbnail_url: str = strawberry.field(resolver=get_photo_thumbnail_url)
    point_of_interest: Optional[PointOfInterest] = strawberry.field(
        resolver=lambda root: poi_dataloader.load(root.point_of_interest_id)
    )
    copilots: List[Copilot] = strawberry.field(resolver=lambda root: copilots_in_photo_dataloader.load(root.id))
    flight: Flight = strawberry.field(resolver=lambda root: flight_dataloader.load(root.flight_id))
    adjustment: Optional[PhotoAdjustment] = strawberry.field(
        resolver=lambda root: photo_adjustment_dataloader.load(root.id)
    )


@strawberry_sqlalchemy_type(models.Flight)
class Flight:
    async def load_gpx_track(root):
        if not root.gpx_track_filename:
            return None

        try:
            gpx_parser = GPXParser(f"{FLIGHT_GPX_TRACK_PATH}/{root.gpx_track_filename}")
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

    pilot: User = strawberry.field(resolver=lambda root: user_dataloader.load(root.created_by_id))
    copilots: Optional[List[Copilot]] = strawberry.field(resolver=load_copilots)
    event: Optional[Event] = strawberry.field(resolver=load_event)
    aircraft: Aircraft = strawberry.field(resolver=lambda root: aircraft_dataloader.load(root.aircraft_id))
    takeoff_airport: Optional[Airport] = strawberry.field(
        resolver=lambda root: airport_dataloader.load(root.takeoff_airport_id)
    )
    landing_airport: Optional[Airport] = strawberry.field(
        resolver=lambda root: airport_dataloader.load(root.landing_airport_id)
    )
    title_photo: Optional[Photo] = strawberry.field(resolver=lambda root: photo_dataloader.load(root.title_photo_id))
    track: List[FlightTrack] = strawberry.field(resolver=lambda root: flight_track_dataloader.load(root.id))
    takeoff_weather_info: Optional[WeatherInfo] = strawberry.field(
        resolver=lambda root: airport_weather_info_loader.load(root.takeoff_weather_info_id)
    )
    landing_weather_info: Optional[WeatherInfo] = strawberry.field(
        resolver=lambda root: airport_weather_info_loader.load(root.landing_weather_info_id)
    )
    photos: List[Photo] = strawberry.field(resolver=lambda root: photos_dataloader.load(root.id))
    gpx_track: Optional[GPXTrack] = strawberry.field(resolver=load_gpx_track)
    duration_min_calculated: int = strawberry.field(
        resolver=lambda root: flight_duration_dataloader.load(root.id)
    )


@strawberry_sqlalchemy_type(models.Copilot)
class Copilot:
    async def resolve_flights(root, info):
        dataloader = public_flights_by_copilot_dataloader
        if info.context.user_id:
            dataloader = flights_by_copilot_dataloader

        return await dataloader.load(root.id)

    flights: List[Flight] = strawberry.field(resolver=resolve_flights)
    photos: List[Photo] = strawberry.field(resolver=lambda root: photo_copilots_dataloader.load(root.id))
    title_photo: Optional[Photo] = strawberry.field(resolver=lambda root: photo_dataloader.load(root.title_photo_id))


@strawberry_sqlalchemy_type(models.Aircraft)
class Aircraft:
    flights: List[Flight] = strawberry.field(resolver=lambda root: flights_by_aircraft_dataloader.load(root.id))
    organization: Optional[Organization] = strawberry.field(
        resolver=lambda root: organizations_dataloader.load(root.organization_id)
    )
    photos: List[Photo] = strawberry.field(resolver=lambda root: photos_aircraft_dataloader.load(root.id))
    title_photo: Optional[Photo] = strawberry.field(resolver=lambda root: photo_dataloader.load(root.title_photo_id))


@strawberry_sqlalchemy_type(models.Organization)
class Organization:
    users: List[User] = strawberry.field(resolver=lambda root: users_in_organization_dataloader.load(root.id))
    aircrafts: List[Aircraft] = strawberry.field(
        resolver=lambda root: aircrafts_from_organization_dataloader.load(root.id)
    )


@strawberry_sqlalchemy_type(models.User, exclude_fields=['password_hashed'])
class User:
    avatar_image_url: Optional[str] = strawberry.field(resolver=lambda root: get_avatar_url(root))
    title_image_url: str = strawberry.field(resolver=lambda root: get_title_image_url(root))
    organizations: List[Organization] = strawberry.field(
        resolver=lambda root: user_organizations_dataloader.load(root.id)
    )


@strawberry_sqlalchemy_type(models.Event)
class Event:
    async def load_flights(root, info):
        is_user_logged_in = bool(info.context.user_id)
        dataloader = flights_by_event_dataloader if is_user_logged_in else public_flights_by_event_dataloader
        return await dataloader.load(root.id)

    flights: List[Flight] = strawberry.field(resolver=load_flights)
