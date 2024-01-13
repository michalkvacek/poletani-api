from datetime import datetime
from typing import Literal
from database import models
from database.transaction import get_session
from external.weather import weather_api
from logger import log


async def download_weather(date_time: datetime, flight_id: int, airport_id: int, type_: Literal['landing', 'takeoff']):
    async with get_session() as db:
        airport = await models.Airport.get_one(db, airport_id)
        gps = (airport.gps_latitude, airport.gps_longitude)

    try:
        weather = await weather_api.get_weather_for_hour(date_time.astimezone(), gps=gps)
        log.warning(weather)
    except Exception as e:
        log.error(f"Error in downloading weather: {e}")
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

    async with get_session() as db:
        flight = await models.Flight.get_one(db, flight_id)
        existing_weather_id = getattr(flight, f'{type_}_weather_info_id')

        if existing_weather_id:
            await models.WeatherInfo.update(db, id=existing_weather_id, data=data)
        else:
            weather_model = await models.WeatherInfo.create(db, data=data)
            await models.Flight.update(db, obj=flight, data={f"{type_}_weather_info_id": weather_model.id})
