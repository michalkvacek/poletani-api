from strawberry.tools import merge_types
from graphql_schema.entities.aircraft import AircraftMutation
from graphql_schema.entities.copilot import CreateCopilotMutation, EditCopilotMutation
from graphql_schema.entities.event import EventMutation
from graphql_schema.entities.flight import FlightMutation
from graphql_schema.entities.organization import OrganizationUserMutation, OrganizationMutation
from graphql_schema.entities.photo import PhotoMutation
from graphql_schema.entities.poi import PointOfInterestMutation
from graphql_schema.entities.user import EditUserMutation

Mutation = merge_types("Mutation", (
    AircraftMutation,
    FlightMutation,
    PhotoMutation,
    PointOfInterestMutation,
    CreateCopilotMutation,
    EditCopilotMutation,
    EditUserMutation,
    EventMutation,
    OrganizationMutation,
    OrganizationUserMutation,
))
