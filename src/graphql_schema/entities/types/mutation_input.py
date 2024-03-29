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


@strawberry_sqlalchemy_input(model=models.Copilot, exclude_fields=["id"], all_optional=True)
class EditCopilotInput(BaseGraphqlInputType):
    pass


@strawberry_sqlalchemy_input(models.PointOfInterest, exclude_fields=['id', 'type_id'])
class CreatePointOfInterestInput(BaseGraphqlInputType):
    type: Optional[ComboboxInput] = None


@strawberry_sqlalchemy_input(models.PointOfInterest, exclude_fields=['id', 'type_id'], all_optional=True)
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


@strawberry_sqlalchemy_input(model=models.Event, exclude_fields=["id"], all_optional=True)
class EditEventInput(BaseGraphqlInputType):
    pass


@strawberry.input
class UploadPhotoInput:
    photo: Upload
    flight_id: int
    name: Optional[str] = None
    description: Optional[str] = None
    point_of_interest: Optional[ComboboxInput] = None


@strawberry.input
class EditPhotoInput:
    name: Optional[str] = None
    description: Optional[str] = None
    point_of_interest: Optional[ComboboxInput] = None
    copilots: Optional[List[ComboboxInput]] = None
    aircraft_id: Optional[int] = None

    def to_dict(self):
        return {
            key: getattr(self, key) for key in ('name', 'description', 'aircraft_id')
            if getattr(self, key) is not None
        }


@strawberry.input
class CropInput(BaseGraphqlInputType):
    left: float
    top: float
    width: float
    height: float


@strawberry.input
class AdjustmentInput:
    rotate: Optional[float] = 0
    crop_after_rotate: Optional[bool] = True,
    brightness: Optional[float] = 1
    contrast: Optional[float] = 1
    saturation: Optional[float] = 1
    sharpness: Optional[float] = 1
    crop: Optional[CropInput] = None


@strawberry_sqlalchemy_input(models.Flight, exclude_fields=[
    "id", "aircraft_id", "deleted", "landing_airport_id", "takeoff_airport_id",
    "takeoff_weather_info_id", "landing_weather_info_id", "gpx_track_filename", "event_id"
], all_optional=True)
class EditFlightInput(BaseGraphqlInputType):
    gpx_track_file: Optional[Upload] = None  # TODO: poresit validaci uploadovaneho souboru!
    track: Optional[List[TrackItemInput]] = None
    copilots: Optional[List[ComboboxInput]] = None
    aircraft: Optional[ComboboxInput] = None
    landing_airport: Optional[ComboboxInput] = None
    takeoff_airport: Optional[ComboboxInput] = None
    event: Optional[ComboboxInput] = None


@strawberry.input()
class CreateFlightInput(BaseGraphqlInputType):
    aircraft: ComboboxInput
    gpx_track_file: Optional[Upload] = None  # TODO: poresit validaci uploadovaneho souboru!
    landing_airport: Optional[ComboboxInput] = None
    takeoff_airport: Optional[ComboboxInput] = None
    takeoff_datetime: Optional[datetime] = None
    landing_datetime: Optional[datetime] = None


@strawberry.input()
class TrackItemInput:
    point_of_interest: Optional[ComboboxInput] = None
    airport: Optional[ComboboxInput] = None
    landing_duration: Optional[int] = None


@strawberry_sqlalchemy_input(models.Aircraft, exclude_fields=['id', 'photo_filename'])
class CreateAircraftInput(BaseGraphqlInputType):
    organization: Optional[ComboboxInput] = None


@strawberry_sqlalchemy_input(models.Aircraft, exclude_fields=['photo_filename'], all_optional=True)
class EditAircraftInput(BaseGraphqlInputType):
    organization: Optional[ComboboxInput] = None
