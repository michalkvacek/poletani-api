from __future__ import annotations
from datetime import datetime
from typing import Optional, List
import strawberry
from strawberry.file_uploads import Upload
from database import models
from graphql_schema.entities.types.base import BaseGraphqlInputType
from graphql_schema.sqlalchemy_to_strawberry_type import strawberry_sqlalchemy_input


@strawberry.input()
class ComboboxInput:
    id: Optional[int] = None
    name: str


@strawberry_sqlalchemy_input(model=models.Copilot, exclude_fields=["id"])
class CreateCopilotInput(BaseGraphqlInputType):
    pass


@strawberry_sqlalchemy_input(model=models.Copilot, exclude_fields=["id"])
class EditCopilotInput(BaseGraphqlInputType):
    pass


@strawberry_sqlalchemy_input(models.PointOfInterest, exclude_fields=['id', 'type_id'])
class CreatePointOfInterestInput(BaseGraphqlInputType):
    type: Optional[ComboboxInput] = None


@strawberry_sqlalchemy_input(models.PointOfInterest, exclude_fields=['id', 'type_id'])
class EditPointOfInterestInput(BaseGraphqlInputType):
    type: Optional[ComboboxInput] = None


@strawberry_sqlalchemy_input(model=models.Organization, exclude_fields=["id"])
class CreateOrganizationInput(BaseGraphqlInputType):
    pass


@strawberry_sqlalchemy_input(model=models.Organization, exclude_fields=["id"])
class EditOrganizationInput(BaseGraphqlInputType):
    pass


@strawberry_sqlalchemy_input(model=models.Event, exclude_fields=["id"])
class CreateEventInput(BaseGraphqlInputType):
    pass


@strawberry_sqlalchemy_input(model=models.Event, exclude_fields=["id"])
class EditEventInput(BaseGraphqlInputType):
    pass


@strawberry_sqlalchemy_input(models.Flight, exclude_fields=[
    "id", "aircraft_id", "deleted", "landing_airport_id", "takeoff_airport_id",
    "takeoff_weather_info_id", "landing_weather_info_id", "gpx_track_filename", "event_id"
], all_optional=True)
class EditFlightInput(BaseGraphqlInputType):
    gpx_track: Optional[Upload] = None  # TODO: poresit validaci uploadovaneho souboru!
    track: Optional[List[TrackItemInput]] = None
    copilots: Optional[List[ComboboxInput]] = None
    aircraft: Optional[ComboboxInput] = None
    landing_airport: Optional[ComboboxInput] = None
    takeoff_airport: Optional[ComboboxInput] = None
    event: Optional[ComboboxInput] = None


@strawberry.input()
class CreateFlightInput(BaseGraphqlInputType):
    aircraft: ComboboxInput
    landing_airport: ComboboxInput
    takeoff_airport: ComboboxInput
    takeoff_datetime: datetime
    landing_datetime: datetime


@strawberry.input()
class TrackItemInput:
    point_of_interest: Optional[ComboboxInput] = None
    airport: Optional[ComboboxInput] = None
    landing_duration: Optional[int] = None


@strawberry_sqlalchemy_input(models.Aircraft, exclude_fields=['id', 'photo_filename'])
class CreateAircraftInput(BaseGraphqlInputType):
    photo: Optional[Upload]
    organization: Optional[ComboboxInput] = None


@strawberry_sqlalchemy_input(models.Aircraft, exclude_fields=['photo_filename'])
class EditAircraftInput(BaseGraphqlInputType):
    photo: Optional[Upload]
    organization: Optional[ComboboxInput] = None
