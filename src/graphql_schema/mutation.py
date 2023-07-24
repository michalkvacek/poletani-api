from strawberry.tools import merge_types
from graphql_schema.entities.aircraft import CreateAircraftMutation, EditAircraftMutation, DeleteAircraftMutation
from graphql_schema.entities.flight import CreateFlightMutation, EditFlightMutation, DeleteFlightMutation
from graphql_schema.entities.photo import UploadPhotoMutation, DeletePhotoMutation, EditPhotoMutation
from graphql_schema.entities.poi import CreatePointOfInterestMutation, EditPointOfInterestMutation

Mutation = merge_types("Mutation", (
    CreateAircraftMutation,
    EditAircraftMutation,
    DeleteAircraftMutation,
    EditFlightMutation,
    DeleteFlightMutation,
    CreateFlightMutation,
    UploadPhotoMutation,
    EditPhotoMutation,
    DeletePhotoMutation,
    CreatePointOfInterestMutation,
    EditPointOfInterestMutation,
))
