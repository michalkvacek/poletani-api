import datetime
import urllib.parse
from typing import Tuple, Dict
import aiohttp
from aiocache import cached


class Weather:
    FORECAST_URL = "https://api.open-meteo.com/v1/forecast?"
    ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive?"
    TIMEZONE = "Europe/Prague"
    METRICS = (
        "pressure_msl", "temperature_2m", "dewpoint_2m", "rain", "cloudcover_low", "cloudcover", "windspeed_10m",
        "winddirection_10m"
    )

    def get_weather_info_url(self, start_date: datetime.date, end_date: datetime.date, gps: Tuple[float, float]) -> str:
        today = datetime.datetime.now().date()
        date_diff = today - end_date

        if date_diff.days >= 7:
            # historical API offers data only older than 5 days
            url = self.ARCHIVE_URL
        else:
            # forecast contains data even 14 days ago
            url = self.FORECAST_URL

        params = {
            "latitude": gps[0],
            "longitude": gps[1],
            "timezone": self.TIMEZONE,
            "hourly": ','.join(self.METRICS),
            "start_date": start_date,
            "end_date": end_date,
        }

        query_string = urllib.parse.urlencode(params)
        return f"{url}{query_string}"

    @cached(ttl=6*3600)
    async def download_weather_for_day(self, date: datetime.date, gps: Tuple[float, float]):
        url = self.get_weather_info_url(start_date=date, end_date=date, gps=gps)

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                resp.raise_for_status()
                return await resp.json()

    async def get_weather_for_hour(self, date_time: datetime.datetime, gps: Tuple[float, float]) -> Dict[str, float|str]:
        data = await self.download_weather_for_day(date_time.date(), gps)

        # TODO: kontrola timezone!
        # TODO: interpolace - udelat vazenyprumer z dvou po sobe jdoucich hodin
        idx = date_time.hour
        result_data = {metric: data['hourly'][metric][idx] for metric in self.METRICS}
        result_data['datetime'] = datetime.datetime.strptime(data['hourly']['time'][idx], "%Y-%m-%dT%H:%M")

        return result_data