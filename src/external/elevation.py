from typing import List, Tuple, Dict

import aiohttp


class ElevationAPI:
    ELEVATION_ENDPOINT = "https://api.open-elevation.com/api/v1/lookup"

    def get_request(self, points: List[Dict[str, float]]):
        return {"locations": [{"latitude": point['lat'], "longitude": point['lng']} for point in points]}

    async def call_api(self, points: List[Dict[str, float]]):
        async with aiohttp.ClientSession() as session:
            async with session.post(self.ELEVATION_ENDPOINT, json=self.get_request(points)) as resp:
                resp.raise_for_status()
                return await resp.json()

    async def get_elevation_for_points(self, points: List[Dict[str, float]]) -> List[dict]:
        response = await self.call_api(points)

        return [{
            "lat": loc['latitude'],
            "lng": loc['longitude'],
            "elevation": loc['elevation']
        } for loc in response['results']]


elevation_api = ElevationAPI()
