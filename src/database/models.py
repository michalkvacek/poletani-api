from __future__ import annotations
import datetime
from typing import Set, List
from sqlalchemy import String, DateTime, ForeignKey, Text, Integer, func, Table, Column, Boolean, select, Float, Enum
from sqlalchemy.orm import Mapped, relationship, as_declarative, mapped_column
from sqlalchemy.ext.asyncio import AsyncSession


@as_declarative()
class BaseModel:
    excluded_columns_in_dict = ("deleted",)

    @classmethod
    def _get_column_names(cls):
        return [col.name for col in cls.__table__.columns]

    def as_dict(self):
        return {c: getattr(self, c) for c in self._get_column_names() if c not in self.excluded_columns_in_dict}

    @classmethod
    async def get_one(cls, db_session: AsyncSession, id: int):
        return (await db_session.scalars(select(cls).filter_by(id=id))).one()

    @classmethod
    async def create(cls, db_session: AsyncSession, data: dict):
        model = cls(**{col: data[col] for col in cls._get_column_names() if col in data})
        db_session.add(model)
        await db_session.flush()

        return model

    @classmethod
    async def update(cls, db_session: AsyncSession, data: dict, obj: BaseModel = None, id: int = None):
        if not obj and not id:
            raise ValueError("Provide either obj or id!")

        if not obj:
            obj = await cls.get_one(db_session, id)
        for key, value in data.items():
            if key in cls._get_column_names() and getattr(obj, key) != value:
                setattr(obj, key, value)

        return obj


user_is_in_organization = Table(
    "user_is_in_organization",
    BaseModel.metadata,
    Column("user_id", Integer, ForeignKey("user.id"), primary_key=True),
    Column("organization_id", Integer, ForeignKey("organization.id"), primary_key=True)
)

flight_has_copilot = Table(
    "flight_has_copilot",
    BaseModel.metadata,
    Column("flight_id", ForeignKey("flight.id"), primary_key=True),
    Column("copilot_id", ForeignKey("copilot.id"), primary_key=True),
)

copilot_has_photo = Table(
    "copilot_has_photo",
    BaseModel.metadata,
    Column("copilot_id", ForeignKey("copilot.id"), primary_key=True),
    Column("photo_id", ForeignKey("photo.id"), primary_key=True),
)


class Airport(BaseModel):
    __tablename__ = "airport"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    icao_code: Mapped[str] = mapped_column(String(8), nullable=False)
    gps_latitude: Mapped[float] = mapped_column(Float, nullable=True)
    gps_longitude: Mapped[float] = mapped_column(Float, nullable=True)
    elevation: Mapped[int] = mapped_column(Integer, nullable=True)
    airport_type: Mapped[str] = mapped_column(Enum("airport", "ull", "heliport"), nullable=False, server_default='airport')  # noqa
    use_in_gpx_guess: Mapped[bool] = mapped_column(Boolean, server_default='1')
    is_public: Mapped[bool] = mapped_column(Boolean, server_default='0')
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey('user.id'), nullable=True)  # automaticky import nebude mit ID  # noqa
    deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default='0')

    metars: Mapped['Metar'] = relationship()
    created_by: Mapped['User'] = relationship()


class PointOfInterestType(BaseModel):
    __tablename__ = "point_of_interest_type"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    icon: Mapped[str] = mapped_column(String(128), nullable=False, server_default='marker')
    is_public: Mapped[bool] = mapped_column(Boolean, server_default='0')
    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey('user.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default='0')

    created_by: Mapped['User'] = relationship()
    points_of_interest: Mapped[List[PointOfInterest]] = relationship()


class PointOfInterest(BaseModel):
    __tablename__ = "point_of_interest"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    url_slug: Mapped[str] = mapped_column(String(128), nullable=False, server_default="")
    title_photo_id: Mapped[int] = mapped_column(Integer, ForeignKey('photo.id'), nullable=True)
    gps_latitude: Mapped[float] = mapped_column(Float, nullable=True)
    gps_longitude: Mapped[float] = mapped_column(Float, nullable=True)
    type_id: Mapped[int] = mapped_column(Integer, ForeignKey("point_of_interest_type.id"), nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, server_default='0')
    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey('user.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default='0')

    type: Mapped[PointOfInterestType] = relationship()
    created_by: Mapped['User'] = relationship()
    title_photo: Mapped['Photo'] = relationship(foreign_keys=[title_photo_id])


class Photo(BaseModel):
    __tablename__ = "photo"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, server_default="")
    description: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    filename: Mapped[str] = mapped_column(String(128), nullable=False)
    filename_extension: Mapped[str] = mapped_column(String(4), nullable=False)
    cache_key: Mapped[str] = mapped_column(String(128), nullable=True)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    exposed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    gps_latitude: Mapped[float] = mapped_column(Float, nullable=True)
    gps_longitude: Mapped[float] = mapped_column(Float, nullable=True)
    gps_altitude: Mapped[float] = mapped_column(Float, nullable=True)
    terrain_elevation: Mapped[float] = mapped_column(Float, nullable=True)
    aircraft_id: Mapped[int] = mapped_column(Integer, ForeignKey("aircraft.id"), nullable=True)
    point_of_interest_id: Mapped[int] = mapped_column(Integer, ForeignKey("point_of_interest.id"), nullable=True)
    flight_id: Mapped[int] = mapped_column(Integer, ForeignKey("flight.id"), nullable=False)
    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey('user.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    flight: Mapped['Flight'] = relationship(foreign_keys=[flight_id])
    point_of_interest: Mapped['PointOfInterest'] = relationship(foreign_keys=[point_of_interest_id])
    adjustment: Mapped['PhotoAdjustment'] = relationship(passive_deletes=True)
    created_by: Mapped['User'] = relationship()
    aircraft: Mapped['Aircraft'] = relationship(foreign_keys=[aircraft_id])
    copilots: Mapped[List['Copilot']] = relationship(secondary=copilot_has_photo)


class PhotoAdjustment(BaseModel):
    __tablename__ = "photo_adjustment"

    id: Mapped[int] = mapped_column(primary_key=True)
    photo_id: Mapped[int] = mapped_column(Integer, ForeignKey('photo.id', ondelete='CASCADE'), nullable=False)
    rotate: Mapped[float] = mapped_column(Float, nullable=True)
    contrast: Mapped[float] = mapped_column(Float, nullable=True)
    brightness: Mapped[float] = mapped_column(Float, nullable=True)
    saturation: Mapped[float] = mapped_column(Float, nullable=True)
    sharpness: Mapped[float] = mapped_column(Float, nullable=True)

    crop_left: Mapped[float] = mapped_column(Float, nullable=True)
    crop_top: Mapped[float] = mapped_column(Float, nullable=True)
    crop_width: Mapped[float] = mapped_column(Float, nullable=True)
    crop_height: Mapped[float] = mapped_column(Float, nullable=True)

    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    photo: Mapped['Photo'] = relationship()


class Aircraft(BaseModel):
    __tablename__ = "aircraft"

    id: Mapped[int] = mapped_column(primary_key=True)
    call_sign: Mapped[str] = mapped_column(String(16), nullable=False)
    title_photo_id: Mapped[int] = mapped_column(Integer, ForeignKey('photo.id'), nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, server_default='0')
    manufacturer: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    model: Mapped[str] = mapped_column(String(30), nullable=False, server_default="")
    seats: Mapped[str] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    organization_id: Mapped[int] = mapped_column(Integer, ForeignKey('organization.id'), nullable=True)
    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey('user.id'), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default='0')

    organization: Mapped['Organization'] = relationship()
    flights: Mapped[Set['Flight']] = relationship()
    created_by: Mapped['User'] = relationship()
    # notes: Mapped['AircraftNotes'] = relationship()


# class AircraftNotes(BaseModel):
#     __tablename__ = "aircraft_notes"
#
#     id: Mapped[int] = mapped_column(primary_key=True)
#     aircraft_id: Mapped[int] = mapped_column(Integer, ForeignKey("aircraft.id"), nullable=False)
#     name: Mapped[str] = mapped_column(String(128), nullable=False)
#     description: Mapped[str] = mapped_column(Text, nullable=False)
#     is_public: Mapped[bool] = mapped_column(Boolean, server_default='0')
#     created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey('user.id'))
#     created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
#
#     created_by: Mapped['User'] = relationship()
#     aircraft: Mapped['Aircraft'] = relationship()


class Organization(BaseModel):
    __tablename__ = "organization"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey('user.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default='0')

    users: Mapped[Set['User']] = relationship(secondary=user_is_in_organization)
    created_by: Mapped['User'] = relationship()


class FlightTrack(BaseModel):
    __tablename__ = "flight_track"

    id: Mapped[int] = mapped_column(primary_key=True)
    flight_id: Mapped[int] = mapped_column(Integer, ForeignKey("flight.id"), nullable=False)
    point_of_interest_id: Mapped[int] = mapped_column(Integer, ForeignKey("point_of_interest.id"), nullable=True)
    airport_id: Mapped[int] = mapped_column(Integer, ForeignKey("airport.id"), nullable=True)
    landing_duration: Mapped[int] = mapped_column(Integer, nullable=True)
    order: Mapped[int] = mapped_column(Integer)

    flight: Mapped['Flight'] = relationship()
    point_of_interest: Mapped['PointOfInterest'] = relationship()
    airport: Mapped['Airport'] = relationship()


class WeatherInfo(BaseModel):
    __tablename__ = "weather_info"

    id: Mapped[int] = mapped_column(primary_key=True)
    qnh: Mapped[int] = mapped_column(Integer, nullable=True)
    temperature_surface: Mapped[Float] = mapped_column(Float, nullable=True)
    dewpoint_surface: Mapped[Float] = mapped_column(Float, nullable=True)
    rain: Mapped[Float] = mapped_column(Float, nullable=True)
    cloudcover_low: Mapped[Float] = mapped_column(Float, nullable=True)
    cloudcover_total: Mapped[Float] = mapped_column(Float, nullable=True)
    wind_speed_surface: Mapped[Float] = mapped_column(Float, nullable=True)
    wind_direction_surface: Mapped[Float] = mapped_column(Float, nullable=True)
    datetime: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class Event(BaseModel):
    __tablename__ = "event"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    url_slug: Mapped[str] = mapped_column(String(128), nullable=False, server_default="")
    date_from: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    date_to: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    organization_id: Mapped[int] = mapped_column(Integer, ForeignKey('organization.id'), nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, server_default='0')
    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey('user.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default='0')

    organization: Mapped['Organization'] = relationship()
    created_by: Mapped['User'] = relationship()


class Flight(BaseModel):
    __tablename__ = "flight"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, server_default="")
    description: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    url_slug: Mapped[str] = mapped_column(String(128), nullable=False, server_default="")
    event_id: Mapped[int] = mapped_column(Integer, ForeignKey("event.id"), nullable=True)
    title_photo_id: Mapped[int] = mapped_column(Integer, ForeignKey('photo.id'), nullable=True)
    takeoff_airport_id: Mapped[int] = mapped_column(Integer, ForeignKey("airport.id"), nullable=True)
    landing_airport_id: Mapped[int] = mapped_column(Integer, ForeignKey("airport.id"), nullable=True)
    takeoff_datetime: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    landing_datetime: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    duration_total: Mapped[int] = mapped_column(Integer, nullable=True)
    duration_pic: Mapped[int] = mapped_column(Integer, nullable=True)
    gpx_track_filename: Mapped[str] = mapped_column(String(128), nullable=True)
    has_terrain_elevation: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    aircraft_id: Mapped[int] = mapped_column(Integer, ForeignKey('aircraft.id'))
    takeoff_weather_info_id: Mapped[int] = mapped_column(Integer, ForeignKey('weather_info.id'), nullable=True)
    landing_weather_info_id: Mapped[int] = mapped_column(Integer, ForeignKey('weather_info.id'), nullable=True)
    landings: Mapped[int] = mapped_column(Integer, default=1)
    is_public: Mapped[bool] = mapped_column(Boolean, server_default='0')
    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey('user.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default='0')

    takeoff_airport: Mapped['Airport'] = relationship(foreign_keys=[takeoff_airport_id])
    landing_airport: Mapped['Airport'] = relationship(foreign_keys=[landing_airport_id])
    weather_info_landing: Mapped[WeatherInfo] = relationship(foreign_keys=[landing_weather_info_id])
    weather_info_takeoff: Mapped[WeatherInfo] = relationship(foreign_keys=[takeoff_weather_info_id])
    track: Mapped['FlightTrack'] = relationship()
    event: Mapped['Event'] = relationship()
    copilots: Mapped[List['Copilot']] = relationship(secondary=flight_has_copilot)
    aircraft: Mapped['Aircraft'] = relationship()
    photos: Mapped[List['Photo']] = relationship(foreign_keys=[Photo.flight_id])
    created_by: Mapped['User'] = relationship()
    title_photo: Mapped['Photo'] = relationship(foreign_keys=[title_photo_id])


class Copilot(BaseModel):
    __tablename__ = "copilot"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    url_slug: Mapped[str] = mapped_column(String(128), nullable=False, server_default="")
    title_photo_id: Mapped[int] = mapped_column(Integer, ForeignKey('photo.id'), nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, server_default='0')
    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey('user.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default='0')

    flights: Mapped[Set['Flight']] = relationship(secondary=flight_has_copilot)
    created_by: Mapped['User'] = relationship()
    photos: Mapped[List['Photo']] = relationship(secondary=copilot_has_photo)
    title_photo: Mapped['Photo'] = relationship(foreign_keys=[title_photo_id])


class Metar(BaseModel):
    __tablename__ = "metar"

    id: Mapped[int] = mapped_column(primary_key=True)
    airport_id: Mapped[int] = mapped_column(Integer, ForeignKey('airport.id'))
    metar: Mapped[str] = mapped_column(Text, nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime)
    deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default='0')

    airport: Mapped['Airport'] = relationship()


class License(BaseModel):
    __tablename__ = "license"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    number: Mapped[str] = mapped_column(String(30), nullable=False)
    valid_until: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey('user.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped['User'] = relationship()
    created_by: Mapped['User'] = relationship()


class User(BaseModel):
    __tablename__ = "user"
    excluded_columns_in_dict = ('password_hashed',)

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    public_username: Mapped[str] = mapped_column(String(128), nullable=True, unique=True)
    avatar_image_filename: Mapped[str] = mapped_column(String(128), nullable=True)
    title_image_filename: Mapped[str] = mapped_column(String(128), nullable=True)
    password_hashed: Mapped[str] = mapped_column(String(60), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    licences: Mapped[Set['License']] = relationship()
    flights: Mapped[Set['Flight']] = relationship()
    organizations: Mapped[Set['Organization']] = relationship(secondary=user_is_in_organization)
