from datetime import timedelta
from typing import List, Optional
import strawberry
from sqlalchemy import select
from database import models
from graphql_schema.dataloaders import copilots_dataloader
from graphql_schema.dataloaders.aircraft import aircraft_dataloader
from graphql_schema.dataloaders.airport import airport_dataloader
from graphql_schema.dataloaders.photos import photos_dataloader, cover_photo_loader
from graphql_schema.entities.aircraft import Aircraft
from graphql_schema.entities.airport import Airport
from graphql_schema.entities.copilot import CopilotType
from graphql_schema.entities.photo import Photo
from graphql_schema.sqlalchemy_to_strawberry_type import strawberry_sqlalchemy_type, strawberry_sqlalchemy_input


# Bude se hodit: https://strawberry.rocks/docs/types/lazy


@strawberry_sqlalchemy_type(models.Flight)
class Flight:
    async def load_takeoff_airport(root):
        return await airport_dataloader.load(root.takeoff_airport_id)

    async def load_landing_airport(root):
        return await airport_dataloader.load(root.landing_airport_id)

    async def load_aircraft(root):
        return await aircraft_dataloader.load(root.aircraft_id)

    async def load_copilot(root):
        return await copilots_dataloader.load(root.copilot_id)

    async def load_photos(root):
        return await photos_dataloader.load(root.id)

    async def load_cover_photo(root):
        return await cover_photo_loader.load(root.id)

    def duration_min_calculated(root):
        if root.duration_total:
            return root.duration_total

        if root.takeoff_datetime and root.landing_datetime:
            diff: timedelta = root.landing_datetime - root.takeoff_datetime
            return diff.seconds / 60

        return 0

    duration_min_calculated: int = strawberry.field(resolver=duration_min_calculated)
    copilot: Optional[CopilotType] = strawberry.field(resolver=load_copilot)
    aircraft: Aircraft = strawberry.field(resolver=load_aircraft)
    takeoff_airport: Airport = strawberry.field(resolver=load_takeoff_airport)
    landing_airport: Airport = strawberry.field(resolver=load_landing_airport)
    cover_photo: Optional[Photo] = strawberry.field(resolver=load_cover_photo)

    photos: List[Photo] = strawberry.field(resolver=load_photos)


def get_base_query(user_id: int):
    return (
        select(models.Flight)
        .filter(models.Flight.created_by_id == user_id)
        .order_by(models.Flight.id.desc())
    )


@strawberry.type
class FlightQueries:
    @strawberry.input
    class FlightFilters:
        takeoff: Optional[int]

    @strawberry.field
    async def flights(root, info, filters: Optional[FlightFilters] = None) -> List[Flight]:
        query = get_base_query(info.context.user_id).order_by(models.Flight.id.desc())

        return (await info.context.db.scalars(query)).all()

    @strawberry.field
    async def flight(root, info, id: int) -> Flight:
        query = (
            get_base_query(info.context.user_id)
            .filter(models.Flight.id == id)
            .filter(models.Flight.deleted.is_(False))
        )
        return (await info.context.db.scalars(query)).one()


@strawberry.type
class CreateFlightMutation:
    @strawberry_sqlalchemy_input(models.Flight, exclude_fields=["id"])
    class CreateFlightInput:
        # photos: Optional[List[Upload]]
        pass

    @strawberry.mutation
    async def create_flight(self, info, input: CreateFlightInput) -> Flight:
        input_data = input.to_dict()

        flight = await models.Flight.create(info.context.db, data={
            **input_data,
            # "photos": [],  # aby se nedelal select pri vytvareni fotek
            "created_by_id": info.context.user_id
        })

        await info.context.db.flush()
        #
        # if input.photos:
        #     photos_dest = f"/app/uploads/photos/{flight.id}/"
        #     for photo in input.photos:
        #         filename = await handle_file_upload(photo, photos_dest)
        #         flight.photos.append(models.Photo(**{
        #             "name": "",
        #             "filename": filename,
        #             "description": "",
        #             "created_by_id": info.context.user_id,
        #         }))

        return flight


@strawberry.type
class EditFlightMutation:
    @strawberry_sqlalchemy_input(models.Flight, exclude_fields=["id"], all_optional=True)
    class EditFlightInput:
        pass

    @strawberry.mutation
    async def edit_flight(self, info, id: int, input: EditFlightInput) -> Flight:
        return await models.Flight.update(info.context.db, id=id, data=input.to_dict())
