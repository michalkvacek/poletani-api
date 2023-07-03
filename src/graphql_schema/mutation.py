from strawberry.tools import merge_types
from graphql_schema.entities.aircraft import CreateAircraftMutation, EditAircraftMutation, DeleteAircraftMutation
from graphql_schema.entities.flight import CreateFlightMutation, EditFlightMutation
from graphql_schema.entities.photo import UploadPhotoMutation, DeletePhotoMutation, EditPhotoMutation

Mutation = merge_types("Mutation", (
    CreateAircraftMutation,
    EditAircraftMutation,
    DeleteAircraftMutation,
    EditFlightMutation,
    CreateFlightMutation,
    UploadPhotoMutation,
    EditPhotoMutation,
    DeletePhotoMutation
))
