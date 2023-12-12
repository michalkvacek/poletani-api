import asyncio
from typing import List, Optional
from sqlalchemy import delete, insert
from sqlalchemy.ext.asyncio import AsyncSession
from strawberry.file_uploads import Upload
from background_jobs.elevation import add_terrain_elevation_to_flight
from background_jobs.weather import download_weather
from database import models
from database.models import flight_has_copilot
from database.transaction import get_session
from graphql_schema.entities.helpers.combobox import handle_combobox_save
from graphql_schema.entities.resolvers.base import BaseMutationResolver, BaseQueryResolver
from graphql_schema.entities.types.mutation_input import EditFlightInput, TrackItemInput, ComboboxInput
from graphql_schema.entities.types.types import Flight
from paths import FLIGHT_GPX_TRACK_PATH
from utils.file import delete_file
from utils.upload import handle_file_upload


class FlightQueryResolver(BaseQueryResolver):
    def __init__(self):
        super().__init__(graphql_type=Flight, model=models.Flight)

    def get_query(
            self,
            user_id: Optional[int] = None,
            object_id: Optional[int] = None,
            only_public: Optional[bool] = False,
            *args,
            **kwargs
    ):
        query = super().get_query(
            user_id, object_id,
            order_by=[models.Flight.takeoff_datetime.desc()],
            only_public=only_public
        )

        if kwargs.get("event_id"):
            query = query.filter(models.Flight.event_id == kwargs['event_id'])

        if kwargs.get("aircraft_id"):
            query = query.filter(models.Flight.aircraft_id == kwargs['aircraft_id'])

        if kwargs.get("copilot_id"):
            query = (
                query.join(models.flight_has_copilot)
                .filter(models.flight_has_copilot.c.copilot_id == kwargs['copilot_id'])
            )

        if kwargs.get("point_of_interest_id"):
            query = (
                query.join(models.Flight.track)
                .filter(models.FlightTrack.point_of_interest_id == kwargs["point_of_interest_id"])
            )

        if kwargs.get('username'):
            query = (
                query.join(models.Flight.created_by)
                .filter(models.User.public_username == kwargs['username'])
            )

        return query


class FlightMutationResolver(BaseMutationResolver):
    def __init__(self):
        super().__init__(Flight, models.Flight)

    async def update(self, context, id: int, input: EditFlightInput) -> Flight:
        user_id = context.user_id
        async with get_session() as db:
            flight = await self._get_one(db, id, user_id)
            flight_data = flight.as_dict()
            flight_id = flight.id

        data = input.to_dict()

        if input.gpx_track is not None:
            data['gpx_track_filename'] = await handle_upload_gpx(flight_data['gpx_track_filename'], input.gpx_track)
            context.background_tasks.add_task(
                add_terrain_elevation_to_flight, flight_id=id, gpx_filename=data['gpx_track_filename']
            )

        async with get_session() as db:
            if input.takeoff_airport:
                takeoff_airport_id = await handle_combobox_save(
                    db, models.Airport, input.takeoff_airport, user_id, name_column="icao_code",
                    extra_data={"name": input.takeoff_airport.name}
                )
                data['takeoff_airport_id'] = takeoff_airport_id
                data['takeoff_datetime'] = input.takeoff_datetime or flight_data['takeoff_datetime']

                context.background_tasks.add_task(
                    download_weather, flight_id=id, airport_id=takeoff_airport_id, date_time=data['takeoff_datetime'],
                    type_="takeoff"
                )

            if input.landing_airport:
                landing_airport_id = await handle_combobox_save(
                    db, models.Airport, input.landing_airport, user_id, name_column="icao_code",
                    extra_data={"name": input.landing_airport.name}
                )

                data['landing_airport_id'] = landing_airport_id
                data['landing_datetime'] = input.landing_datetime or flight_data['landing_datetime']

                context.background_tasks.add_task(
                    download_weather, flight_id=id, airport_id=landing_airport_id, date_time=data['landing_datetime'],
                    type_="landing"
                )

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
                copilots = await asyncio.gather(*[
                    handle_combobox_save(db, models.Copilot, copilot, user_id) for copilot in input.copilots
                ])

                for copilot_id in copilots:
                    await db.execute(insert(flight_has_copilot).values(flight_id=flight_id, copilot_id=copilot_id))

            return await self._do_update(db, flight_data, data)


async def handle_upload_gpx(original_gpx_filename: str, gpx_track: Upload):
    if original_gpx_filename:
        delete_file(FLIGHT_GPX_TRACK_PATH + "/" + original_gpx_filename, silent=True)

    return await handle_file_upload(gpx_track, FLIGHT_GPX_TRACK_PATH)


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
                "landing_duration": item.landing_duration if airport_id else None
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
