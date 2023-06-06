from __future__ import annotations
import datetime
from typing import Set
from sqlalchemy import String, DateTime, ForeignKey, Text, Integer, func, Table, Column, Boolean, select
from sqlalchemy.orm import Mapped, relationship, as_declarative, mapped_column
from database.custom_types import Point
from sqlalchemy.ext.asyncio import AsyncSession


@as_declarative()
class BaseModel:
    excluded_columns_in_dict = tuple()

    def as_dict(self):
        return {
            c.name: getattr(self, c.name)
            for c in self.__table__.columns
            if c.name not in self.excluded_columns_in_dict
        }

    @classmethod
    async def get_one(cls, db_session: AsyncSession, id: int):
        return (await db_session.scalars(select(cls).filter_by(id=id))).one()

    @classmethod
    async def create(cls, db_session: AsyncSession, data: dict):
        model = cls(**data)
        db_session.add(model)
        await db_session.commit()

        return model

    @classmethod
    async def update(cls, db_session: AsyncSession, data: dict, obj: BaseModel = None, id: int = None):
        if not obj and not id:
            raise ValueError("Provide either obj or id!")

        if not obj:
            obj = await cls.get_one(db_session, id)
        for key, value in data.items():
            if getattr(obj, key) != value:
                setattr(obj, key, value)

        await db_session.commit()

        return obj


# TODO: doplnit GPX k letu, pocasi k letu (podle lokality, mozna do FlightTrack)

user_is_in_organization = Table(
    "user_is_in_organization",
    BaseModel.metadata,
    Column("user_id", Integer, ForeignKey("user.id"), primary_key=True),
    Column("organization_id", Integer, ForeignKey("organization.id"), primary_key=True)
)


class Airport(BaseModel):
    __tablename__ = "airport"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    icao_code: Mapped[str] = mapped_column(String(4), nullable=False)
    gps_position: Mapped[Point] = mapped_column(Point, nullable=True)
    elevation: Mapped[int] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default='0')

    metars: Mapped['Metar'] = relationship(back_populates="airport")


class PointOfInterestType(BaseModel):
    __tablename__ = "point_of_interest_type"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, server_default='0')
    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey('user.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default='0')

    created_by: Mapped['User'] = relationship()


class PointOfInterest(BaseModel):
    __tablename__ = "point_of_interest"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    gps_position: Mapped[Point] = mapped_column(Point, nullable=True)
    type_id: Mapped[int] = mapped_column(Integer, ForeignKey("point_of_interest_type.id"))
    is_public: Mapped[bool] = mapped_column(Boolean, server_default='0')
    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey('user.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default='0')

    type: Mapped[PointOfInterestType] = relationship()
    created_by: Mapped['User'] = relationship()


class Photo(BaseModel):
    __tablename__ = "photo"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    filename: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    gps_position: Mapped[Point] = mapped_column(Point, nullable=True)
    flight_id: Mapped[int] = mapped_column(Integer, ForeignKey("flight.id"), nullable=False)
    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey('user.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    flight: Mapped['Flight'] = relationship(back_populates="photos")
    created_by: Mapped['User'] = relationship()


class Aircraft(BaseModel):
    __tablename__ = "aircraft"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    photo_filename: Mapped[str] = mapped_column(String(128), nullable=True)
    manufacturer: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    model: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    organization_id: Mapped[int] = mapped_column(Integer, ForeignKey('organization.id'), nullable=True)
    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey('user.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default='0')

    organization: Mapped['Organization'] = relationship()
    flights: Mapped[Set['Flight']] = relationship()
    created_by: Mapped['User'] = relationship()
    notes: Mapped['AircraftNotes'] = relationship()


class AircraftNotes(BaseModel):
    __tablename__ = "aircraft_notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    aircraft_id: Mapped[int] = mapped_column(Integer, ForeignKey("aircraft.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, server_default='0')
    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey('user.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    created_by: Mapped['User'] = relationship()
    aircraft: Mapped['Aircraft'] = relationship(back_populates="notes")


class Organization(BaseModel):
    __tablename__ = "organization"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey('user.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default='0')

    users: Mapped[Set['User']] = relationship(back_populates='organizations', secondary=user_is_in_organization)
    created_by: Mapped['User'] = relationship()


class FlightTrack(BaseModel):
    __tablename__ = "flight_track"

    id: Mapped[int] = mapped_column(primary_key=True)
    flight_id: Mapped[int] = mapped_column(Integer, ForeignKey("flight.id"), nullable=False)
    poi_id: Mapped[int] = mapped_column(Integer, ForeignKey("point_of_interest.id"), nullable=False)
    order: Mapped[int] = mapped_column(Integer)

    flight: Mapped['Flight'] = relationship()
    point_of_interest: Mapped['PointOfInterest'] = relationship()


class Flight(BaseModel):
    __tablename__ = "flight"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    takeoff_datetime: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    landing_datetime: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    duration_pic: Mapped[int] = mapped_column(Integer, nullable=False)
    takeoff_airport_id: Mapped[int] = mapped_column(Integer, ForeignKey("airport.id"), nullable=True)
    landing_airport_id: Mapped[int] = mapped_column(Integer, ForeignKey("airport.id"), nullable=True)
    aircraft_id: Mapped[int] = mapped_column(Integer, ForeignKey('aircraft.id'))
    copilot_id: Mapped[int] = mapped_column(Integer, ForeignKey('copilot.id'), nullable=True)

    solo: Mapped[bool] = mapped_column(Boolean, default=True)
    with_instructor: Mapped[bool] = mapped_column(Boolean, default=False)
    landings: Mapped[int] = mapped_column(Integer, default=1)

    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey('user.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default='0')

    takeoff_airport: Mapped['Airport'] = relationship(foreign_keys=[takeoff_airport_id])
    landing_airport: Mapped['Airport'] = relationship(foreign_keys=[landing_airport_id])
    copilot: Mapped['Copilot'] = relationship(back_populates="flights")
    aircraft: Mapped['Aircraft'] = relationship(back_populates="flights")
    photos: Mapped[Set['Photo']] = relationship()
    user: Mapped['User'] = relationship(back_populates="flights")
    created_by: Mapped['User'] = relationship()

    # flight_track: Mapped[List['PointOfInterest']] = relationship(secondary=FlightTrack)


class Copilot(BaseModel):
    __tablename__ = "copilot"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey('user.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default='0')

    flights: Mapped[Set['Flight']] = relationship(back_populates="copilot")
    created_by: Mapped['User'] = relationship()


class Metar(BaseModel):
    __tablename__ = "metar"

    id: Mapped[int] = mapped_column(primary_key=True)
    airport_id: Mapped[int] = mapped_column(Integer, ForeignKey('airport.id'))
    metar: Mapped[str] = mapped_column(Text, nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime)
    deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default='0')

    airport: Mapped['Airport'] = relationship(back_populates="metars")


class License(BaseModel):
    __tablename__ = "license"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    number: Mapped[str] = mapped_column(String(30), nullable=False)
    valid_until: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey('user.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped['User'] = relationship(back_populates="licences")
    created_by: Mapped['User'] = relationship()


class User(BaseModel):
    __tablename__ = "user"
    excluded_columns_in_dict = ('password_hashed',)

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    avatar_image_url: Mapped[str] = mapped_column(String(128), nullable=True)
    password_hashed: Mapped[str] = mapped_column(String(60), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    licences: Mapped[Set['License']] = relationship(back_populates="user")
    flights: Mapped[Set['Flight']] = relationship(back_populates="user")
    organizations: Mapped[Set['Organization']] = relationship(back_populates="users", secondary=user_is_in_organization)
