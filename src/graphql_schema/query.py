from strawberry.tools import merge_types
from .entities.aircraft import AircraftQueries
from .entities.airport import AirportQueries
from .entities.copilot import CopilotQueries
from .entities.event import EventQueries
from .entities.flight import FlightQueries
from .entities.organization import OrganizationQueries
from .entities.photo import PhotoQueries
from .entities.poi import PointOfInterestQueries
from .entities.poi_type import PointOfInterestTypeQueries
from .entities.user import UserQueries

# https://github.com/strawberry-graphql/examples/blob/main/fastapi-sqlalchemy/api/schema.py


Query = merge_types('Query', (
    AircraftQueries,
    AirportQueries,
    FlightQueries,
    CopilotQueries,
    UserQueries,
    PhotoQueries,
    PointOfInterestQueries,
    PointOfInterestTypeQueries,
    EventQueries,
    OrganizationQueries,
))
