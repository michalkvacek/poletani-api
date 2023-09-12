import asyncio
import sys

from sqlalchemy import select

sys.path.insert(0, "/app/src")

from database import async_session, models
from external.elevation import elevation_api
from external.gpx_parser import GPXParser


async def add_elevation_to_photos():
    async with async_session() as session:
        photos = (await session.scalars(
            select(models.Photo)
            .filter(models.Photo.terrain_elevation.is_(None))
        )).all()

        coordinates = [{"lat": p.gps_latitude, "lng": p.gps_longitude} for p in photos if p.gps_latitude or p.gps_longitude]
        photos_by_corrdinates = {(p.gps_latitude, p.gps_longitude): p for p in photos}
        if not coordinates:
            print("all done")
            return

        points = await elevation_api.get_elevation_for_points(coordinates)
        for point in points:
            photo = photos_by_corrdinates[point['lat'], point['lng']]
            await models.Photo.update(db_session=session, obj=photo, data={"terrain_elevation": point['elevation']})
        await session.flush()
        await session.commit()


async def add_elevation_to_tracks():
    async with async_session() as session:
        flights = (await session.scalars(
            select(models.Flight)
            .filter(models.Flight.has_terrain_elevation == False)
            .filter(models.Flight.gpx_track_filename.isnot(None))
        )).all()

        if not flights:
            print("all done")
            return

        for flight in flights:
            gpx_file = f"/app/uploads/tracks/{flight.gpx_track_filename}"
            gpx = GPXParser(gpx_file)

            coordinates = await gpx.get_coordinates()
            elevation = await elevation_api.get_elevation_for_points(coordinates)
            gpx_with_elevation = gpx.add_terrain_elevation(elevation)

            output_name = f"terrain_{flight.gpx_track_filename[30:]}"
            gpx.write(gpx_with_elevation, output=f"/app/uploads/tracks/{output_name}")
            await models.Flight.update(
                db_session=session, obj=flight, data={
                    "has_terrain_elevation": True,
                    "gpx_track_filename": output_name
                }
            )
        await session.flush()
        await session.commit()


async def run_all():
    await asyncio.gather(add_elevation_to_photos(), add_elevation_to_tracks())


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_all())
