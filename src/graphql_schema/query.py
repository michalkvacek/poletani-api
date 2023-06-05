from strawberry.tools import merge_types
from .entities.aircraft import AircraftQueries
from .entities.copilot import CopilotQueries
from .entities.flight import FlightQueries
from .entities.user import UserQueries

# https://github.com/strawberry-graphql/examples/blob/main/fastapi-sqlalchemy/api/schema.py


Query = merge_types('Query', (
    AircraftQueries,
    FlightQueries,
    CopilotQueries,
    UserQueries
))
