from aiohttp import ClientResponseError
from database import models
from dependencies.db import get_session
from external.elevation import elevation_api
from external.gpx_parser import GPXParser


async def add_terrain_elevation_to_flight(flight: dict, gpx_filename: str):
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


async def add_terrain_elevation_to_photo(photo):
    async with get_session() as db:
        try:
            elevation = await elevation_api.get_elevation_for_points([
                {"lat": photo.gps_latitude, "lng": photo.gps_longitude}
            ])
            if not elevation:
                print("Cannot get elevation")
                return

            terrain_elevation = elevation[0]['elevation']
            await models.Photo.update(db_session=db, obj=photo, data={"terrain_elevation": terrain_elevation})
        except Exception as e:
            print(f"Cannot get elevation: {e}")
