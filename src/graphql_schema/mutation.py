from strawberry.tools import merge_types
from graphql_schema.entities.aircraft import CreateAircraftMutation, EditAircraftMutation, DeleteAircraftMutation
from graphql_schema.entities.copilot import CreateCopilotMutation, EditCopilotMutation
from graphql_schema.entities.event import CreateEventMutation, EditEventMutation
from graphql_schema.entities.flight import FlightMutation
from graphql_schema.entities.organization import (
    CreateOrganizationMutation, EditOrganizationMutation, OrganizationUserMutation
)
from graphql_schema.entities.photo import UploadPhotoMutation, DeletePhotoMutation, EditPhotoMutation
from graphql_schema.entities.poi import CreatePointOfInterestMutation, EditPointOfInterestMutation
from graphql_schema.entities.user import EditUserMutation

Mutation = merge_types("Mutation", (
    CreateAircraftMutation,
    EditAircraftMutation,
    DeleteAircraftMutation,
    FlightMutation,
    UploadPhotoMutation,
    EditPhotoMutation,
    DeletePhotoMutation,
    CreatePointOfInterestMutation,
    EditPointOfInterestMutation,
    CreateCopilotMutation,
    EditCopilotMutation,
    EditUserMutation,
    CreateEventMutation,
    EditEventMutation,
    CreateOrganizationMutation,
    EditOrganizationMutation,
    OrganizationUserMutation,
))
