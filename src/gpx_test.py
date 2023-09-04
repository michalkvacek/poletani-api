import asyncio
from external.elevation import ElevationAPI
from external.gpx_parser import GPXParser


async def test():
    elevation_api = ElevationAPI()
    parser = GPXParser("./uploads/tracks/37b979cb-71c0-4d09-a2c1-cfdad5f7a0cf-OK-AUR_28_AUR_Bristell_NG5_Zapisnik_letu_2023-08-04-00 00_2023-08-04-12 00(1).gpx")
    points = await parser.get_coordinates()
    elevation = await elevation_api.get_elevation_for_points(points)
    parser.add_terrain_elevation(elevation)

asyncio.run(test())