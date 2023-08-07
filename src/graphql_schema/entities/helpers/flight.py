from datetime import datetime
from typing import List, Type
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from database import models
from external.weather import Weather
from graphql_schema.types import ComboboxInput

weather_api = Weather()


async def handle_weather_info(db: AsyncSession, date_time: datetime, airport: models.Airport) -> models.WeatherInfo:
    weather = await weather_api.get_weather_for_hour(date_time, (airport.gps_latitude, airport.gps_longitude))

    return await models.WeatherInfo.create(db_session=db, data={
        "datetime": weather['datetime'],
        "qnh": weather['pressure_msl'],
        "temperature_surface": weather['temperature_2m'],
        "dewpoint_surface": weather['dewpoint_2m'],
        "rain": weather['rain'],
        "cloudcover_total": weather['cloudcover'],
        "cloudcover_low": weather['cloudcover_low'],
        "wind_speed_surface": weather['windspeed_10m'],
        "wind_direction_surface": weather['winddirection_10m'],
    })


async def handle_track_edit(db: AsyncSession, flight: models.Flight, track: List[ComboboxInput], user_id: int):
    await db.execute(delete(models.FlightTrack).filter(models.FlightTrack.flight_id == flight.id))

    existing_poi_ids = [i.id for i in track if i.id]
    poi_query = (
        select(models.PointOfInterest)
        .filter(models.PointOfInterest.created_by_id == user_id)
        .filter(models.PointOfInterest.id.in_(existing_poi_ids))
    )
    pois = (await db.scalars(poi_query)).all()
    poi_map = {poi.id: poi for poi in pois}

    order = 0
    for item in track:
        poi_object = None
        if item.id:
            poi_object = poi_map.get(item.id)

        if not poi_object:
            poi_object = await models.PointOfInterest.create(db, data=dict(created_by_id=user_id, name=item.name))
            await db.flush()

        await models.FlightTrack.create(
            db,
            data={
                "flight_id": flight.id,
                "point_of_interest_id": poi_object.id,
                "order": order
            }
        )
        order += 1


async def handle_aircraft_save(db: AsyncSession, user_id: int, aircraft: ComboboxInput):
    if aircraft.id:
        return aircraft.id
    else:
        obj = await models.Aircraft.create(db, {
            "call_sign": aircraft.name,
            "description": "",
            "model": "",
            "manufacturer": "",
            "created_by_id": user_id

        })
        await db.flush()
        return obj.id


async def handle_copilot_edit(db: AsyncSession, copilot: ComboboxInput, user_id: int) -> int:
    return await handle_combobox_save(db, models.Copilot, copilot, user_id)


async def handle_combobox_save(
        db: AsyncSession, model: Type[models.BaseModel],
        input: ComboboxInput,
        user_id: int,
        name_column: str = "name"
):
    if input.id:
        return input.id
    else:
        data = {name_column: input.name}
        if hasattr(model, "created_by_id"):
            data["created_by_id"] = user_id

        obj = await model.create(db, data)
        await db.flush()
        return obj.id
