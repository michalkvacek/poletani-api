from database import models
from dependencies.db import get_session
from external.elevation import elevation_api


async def add_terrain_elevation(photo):
    async with get_session() as db:
        try:
            elevation = await elevation_api.get_elevation_for_points([{"lat": photo.gps_latitude, "lng": photo.gps_longitude}])
            if not elevation:
                print("Cannot get elevation")
                return

            terrain_elevation = elevation[0]['elevation']
            await models.Photo.update(db_session=db, obj=photo, data={"terrain_elevation": terrain_elevation})
        except Exception as e:
            print(f"Cannot get elevation: {e}")


