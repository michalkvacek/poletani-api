from typing import List, Optional
import strawberry
from sqlalchemy import select
from database import models
from graphql_schema.dataloaders import copilots_dataloader
from graphql_schema.dataloaders.aircraft import aircraft_dataloader
from graphql_schema.entities.aircraft import Aircraft
from graphql_schema.entities.copilot import CopilotType
from graphql_schema.sqlalchemy_to_strawberry_type import strawberry_sqlalchemy_type, strawberry_sqlalchemy_input


# Bude se hodit: https://strawberry.rocks/docs/types/lazy

@strawberry_sqlalchemy_type(models.Flight)
class Flight:

    async def load_aircraft(root):
        return await aircraft_dataloader.load(root.aircraft_id)

    async def load_copilot(root):
        return await copilots_dataloader.load(root.copilot_id)

    copilot: Optional[CopilotType] = strawberry.field(resolver=load_copilot)
    aircraft: Aircraft = strawberry.field(resolver=load_aircraft)


@strawberry.type
class FlightQueries:
    @strawberry.input
    class FlightFilters:
        takeoff: Optional[int]

    @strawberry.field
    async def flights(root, info, filters: Optional[FlightFilters] = None) -> List[Flight]:
        query = (
            select(models.Flight)
            .filter(models.Flight.created_by_id == info.context.user_id)
            .order_by(models.Flight.id)  # TODO: desc
        )

        return (await info.context.db.scalars(query)).all()

    @strawberry.field
    async def flight(root, info, id: int) -> Flight:
        query = (
            select(models.Flight)
            .filter(models.Flight.id == id)
            .filter(models.Flight.created_by_id == info.context.user_id)
        )
        return (await info.context.db.scalars(query)).fetch_one()


@strawberry.type
class CreateFlightMutation:
    @strawberry_sqlalchemy_input(models.Flight, all_optional=True)
    class FlightInput:
        pass

    @strawberry.mutation
    async def create_flight(self, info, input_: FlightInput) -> Flight:
        model = models.Flight(name=input_.name)

        db = info.context.db
        db.add(model)
        await db.commit()

        return Flight(model)
