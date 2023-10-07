import asyncio
from datetime import datetime
from typing import List, Optional, Type

from aiocache import cached
from sqlalchemy import delete, insert
from sqlalchemy.ext.asyncio import AsyncSession
from strawberry.file_uploads import Upload

from background_jobs.elevation import add_terrain_elevation_to_flight
from database import models
from database.models import flight_has_copilot
from dependencies.db import get_session
from external.weather import weather_api
from graphql_schema.entities.helpers.combobox import handle_combobox_save
from graphql_schema.entities.resolvers.base import get_base_resolver
from graphql_schema.entities.types.mutation_input import EditFlightInput, TrackItemInput, ComboboxInput
from graphql_schema.entities.types.types import Flight
from upload_utils import delete_file, handle_file_upload


class BaseMutationResolver:
    model: Type[models.BaseModel]
    graphql_type = Flight

    @classmethod
    async def delete(cls, user_id: int, id: int):
        async with get_session() as db:
            model = (
                (await db.scalars(
                    get_base_resolver(cls.model, user_id=user_id, object_id=id)
                    .filter(cls.model.id == id))
                 )
                .one()
            )

            if hasattr(cls.model, "deleted"):
                model = await cls.model.update(db, obj=model, data=dict(deleted=True))
            else:
                db.delete(model)

            return cls.graphql_type(**model.as_dict())

    @classmethod
    async def _do_update(cls, db: AsyncSession, obj: models.BaseModel | dict, data: dict):
        update_where = {}
        if isinstance(obj, models.BaseModel):
            update_where['obj'] = obj
        else:
            update_where['id'] = obj['id']

        model = await cls.model.update(db, data=data, **update_where)
        return cls.graphql_type(**model.as_dict())


async def handle_upload_gpx(original_gpx_filename: str, gpx_track: Upload):
    path = "/app/uploads/tracks"

    if original_gpx_filename:
        delete_file(path + "/" + original_gpx_filename, silent=True)

    return await handle_file_upload(gpx_track, path)


class FlightMutationResolver(BaseMutationResolver):
    model = models.Flight
    graphql_type = Flight

    async def create(self):
        pass

    @classmethod
    async def update(cls, context, id: int, input: EditFlightInput):
        user_id = context.user_id
        async with get_session() as db:
            flight = (await db.scalars(get_base_resolver(models.Flight, user_id=user_id, object_id=id))).one()
            flight_data = flight.as_dict()
            flight_id = flight.id

        data = input.to_dict()

        if input.gpx_track is not None:
            data['gpx_track_filename'] = await handle_upload_gpx(flight_data['gpx_track_filename'], input.gpx_track)
            context.background_tasks.add_task(
                add_terrain_elevation_to_flight, flight_id=id, gpx_filename=data['gpx_track_filename']
            )

        async with get_session() as db:
            if input.landing_airport:
                landing_airport = await get_airport(db, input.landing_airport, user_id)
                landing_datetime = input.landing_datetime or flight_data['landing_datetime']

                data['landing_airport_id'] = landing_airport.id
                data['landing_datetime'] = landing_datetime

                weather_info = await handle_weather_info(db, landing_datetime, landing_airport, flight_data['landing_weather_info_id'])
                if weather_info:
                    data['landing_weather_info_id'] = weather_info.id

            if input.takeoff_airport:
                takeoff_airport = await get_airport(db, input.takeoff_airport, user_id)
                takeoff_datetime = input.takeoff_datetime or flight_data['takeoff_datetime']

                data['takeoff_airport_id'] = takeoff_airport.id
                data['takeoff_datetime'] = takeoff_datetime

                weather_info = await handle_weather_info(db, takeoff_datetime, takeoff_airport, flight_data['takeoff_weather_info_id'])
                if weather_info:
                    data['takeoff_weather_info_id'] = weather_info.id

            if input.aircraft is not None:
                data['aircraft_id'] = await handle_aircraft_save(db, user_id, input.aircraft)

            if input.event is not None:
                data['event_id'] = await handle_combobox_save(
                    db,
                    model=models.Event,
                    input=input.event,
                    extra_data={"description": "", "is_public": False},
                    user_id=context.user_id
                )

            if input.track is not None:
                await handle_track_edit(db=db, flight_id=flight_id, track=input.track, user_id=user_id)

            if input.copilots is not None:
                await db.execute(delete(flight_has_copilot).filter_by(flight_id=flight_id))
                copilots = await handle_copilots_edit(db, input.copilots or [], user_id)
                for copilot_id in copilots:
                    await db.execute(insert(flight_has_copilot).values(flight_id=flight_id, copilot_id=copilot_id))

            return await cls._do_update(db, flight_data, data)


async def handle_weather_info(
        db: AsyncSession, date_time: datetime, airport: models.Airport, existing_weather_id: Optional[int] = None
) -> Optional[models.WeatherInfo]:
    if not airport.gps_latitude or not airport.gps_longitude:
        return None

    try:
        weather = await weather_api.get_weather_for_hour(
            date_time.astimezone(),
            gps=(airport.gps_latitude, airport.gps_longitude)
        )
    except Exception as e:
        print(e)
        return None

    data = {
        "datetime": weather['datetime'],
        "qnh": weather['pressure_msl'],
        "temperature_surface": weather['temperature_2m'],
        "dewpoint_surface": weather['dewpoint_2m'],
        "rain": weather['rain'],
        "cloudcover_total": weather['cloudcover'],
        "cloudcover_low": weather['cloudcover_low'],
        "wind_speed_surface": weather['windspeed_10m'],
        "wind_direction_surface": weather['winddirection_10m'],
    }

    if existing_weather_id:
        model = await models.WeatherInfo.update(db, id=existing_weather_id, data=data)
    else:
        model = await models.WeatherInfo.create(db, data=data)

    return model


async def handle_track_edit(db: AsyncSession, flight_id: int, track: List[TrackItemInput], user_id: int):
    await db.execute(delete(models.FlightTrack).filter(models.FlightTrack.flight_id == flight_id))

    order = 0
    for item in track:
        poi_id = None
        airport_id = None
        if item.point_of_interest:
            poi_id = await handle_combobox_save(
                db, models.PointOfInterest, item.point_of_interest, user_id, extra_data={"description": ""}
            )

        if item.airport:
            airport_id = await handle_combobox_save(
                db, models.Airport, item.airport, user_id,
                name_column="icao_code",
                extra_data={"name": item.airport.name}
            )

        await models.FlightTrack.create(
            db,
            data={
                "flight_id": flight_id,
                "point_of_interest_id": poi_id,
                "airport_id": airport_id,
                "order": order,
                "landing_duration": item.landing_duration
            }
        )
        order += 1


async def handle_aircraft_save(db: AsyncSession, user_id: int, aircraft: ComboboxInput):
    return await handle_combobox_save(
        db, models.Aircraft, aircraft, user_id,
        name_column="call_sign",
        extra_data={
            "description": "",
            "model": "",
            "seats": 2,
            "manufacturer": "",
        })


@cached()
async def get_airport(db: AsyncSession, input: ComboboxInput, user_id: int):
    airport_id = await handle_combobox_save(
        db, models.Airport, input, user_id, name_column="icao_code", extra_data={"name": input.name}
    )

    return (await db.scalars(get_base_resolver(models.Airport, object_id=airport_id))).one()


async def handle_copilots_edit(db: AsyncSession, copilots: List[ComboboxInput], user_id: int) -> tuple:
    cors = [handle_combobox_save(db, models.Copilot, copilot, user_id) for copilot in copilots]
    return await asyncio.gather(*cors)
