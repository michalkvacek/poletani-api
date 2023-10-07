from __future__ import annotations
from typing import Optional, List
import strawberry
from strawberry.file_uploads import Upload
from database import models
from graphql_schema.sqlalchemy_to_strawberry_type import strawberry_sqlalchemy_input


@strawberry.input()
class ComboboxInput:
    id: Optional[int] = None
    name: str


@strawberry_sqlalchemy_input(models.Flight, exclude_fields=[
    "id", "aircraft_id", "deleted", "landing_airport_id", "takeoff_airport_id",
    "takeoff_weather_info_id", "landing_weather_info_id", "gpx_track_filename"
], all_optional=True)
class EditFlightInput:
    gpx_track: Optional[Upload] = None  # TODO: poresit validaci uploadovaneho souboru!
    track: Optional[List[TrackItemInput]] = None
    copilots: Optional[List[ComboboxInput]] = None
    aircraft: Optional[ComboboxInput] = None
    landing_airport: Optional[ComboboxInput] = None
    takeoff_airport: Optional[ComboboxInput] = None
    event: Optional[ComboboxInput] = None


@strawberry_sqlalchemy_input(models.Flight, exclude_fields=[
    "id", "aircraft_id", "landing_airport_id", "takeoff_airport_id", "weather_info_takeoff_id",
    "weather_info_landing_id", "with_instructor", "has_terrain_elevation"
])
class CreateFlightInput:
    aircraft: ComboboxInput
    landing_airport: ComboboxInput
    takeoff_airport: ComboboxInput


@strawberry.input()
class TrackItemInput:
    # order: int
    point_of_interest: Optional[ComboboxInput] = None
    airport: Optional[ComboboxInput] = None
    landing_duration: Optional[int] = None
