from aiohttp import ClientResponseError
from database import models
from dependencies.db import get_session
from external.elevation import elevation_api
from external.gpx_parser import GPXParser


async def add_terrain_elevation(flight: dict, gpx_filename: str):
    path = "/app/uploads/tracks"  # TODO vytahnout do configu

    gpx_parser = GPXParser(f"{path}/{gpx_filename}")
    coordinates = await gpx_parser.get_coordinates()

    try:
        elevation = await elevation_api.get_elevation_for_points(coordinates)
        tree_with_elevation = gpx_parser.add_terrain_elevation(elevation)
        output_name = f"terrain_{gpx_filename}"
        gpx_parser.write(tree_with_elevation, f"{path}/{output_name}")

        async with get_session() as db:
            await models.Flight.update(
                db, {"gpx_track_filename": output_name, "has_terrain_elevation": True},
                id=flight['id'])

    except ClientResponseError as e:
        print(e)
