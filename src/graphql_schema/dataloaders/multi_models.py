from strawberry.dataloader import DataLoader
from database import models
from graphql_schema.dataloaders.base import MultiModelsDataloader

# TODO: doresit razeni modelu!

aircrafts_from_organization_dataloader = DataLoader(
    load_fn=MultiModelsDataloader(
        models.Aircraft,
        relationship_column=models.Organization.id,
        extra_join=[models.Aircraft.organization]
    ).load,
    cache=False
)

flight_copilots_dataloader = DataLoader(
    load_fn=MultiModelsDataloader(
        models.Copilot,
        relationship_column=models.Flight.id,
        extra_join=[models.Copilot.flights]).load,
    cache=False)

flights_by_copilot_dataloader = DataLoader(
    load_fn=MultiModelsDataloader(
        models.Flight,
        relationship_column=models.Copilot.id,
        extra_join=[models.Flight.copilots]).load,
    cache=False
)
flights_by_aircraft_dataloader = DataLoader(
    load_fn=MultiModelsDataloader(
        models.Flight,
        relationship_column=models.Flight.aircraft_id
    ).load, cache=False)
flight_by_poi_dataloader = DataLoader(
    load_fn=MultiModelsDataloader(
        models.Flight,
        relationship_column=models.PointOfInterest.id,
        extra_join=[models.Flight.track, models.PointOfInterest]).load,
    cache=False
)

flights_by_event_dataloader = DataLoader(
    load_fn=MultiModelsDataloader(
        models.Flight,
        relationship_column=models.Event.id,
        extra_join=[models.Flight.event]).load,
    cache=False
)

user_organizations_dataloader = DataLoader(load_fn=MultiModelsDataloader(
    models.Organization,
    relationship_column=models.user_is_in_organization.c.user_id,
    extra_join=[models.user_is_in_organization]
).load, cache=False)

users_in_organization_dataloader = DataLoader(
    load_fn=MultiModelsDataloader(
        models.User,
        relationship_column=models.Organization.id,
        extra_join=[models.Organization.users]
    ).load,
    cache=False
)

photos_dataloader = DataLoader(
    load_fn=MultiModelsDataloader(
        models.Photo,
        relationship_column=models.Photo.flight_id,
        order_by=[models.Photo.exposed_at]
    ).load,
    cache=False
)
poi_photos_dataloader = DataLoader(
    load_fn=MultiModelsDataloader(
        models.Photo,
        relationship_column=models.Photo.point_of_interest_id,
        order_by=[models.Photo.exposed_at]
    ).load,
    cache=False
)
flight_track_dataloader = DataLoader(
    load_fn=MultiModelsDataloader(
        models.FlightTrack,
        relationship_column=models.FlightTrack.flight_id,
        order_by=[models.FlightTrack.order]
    ).load,
    cache=False
)
