from typing import Optional, Type
from strawberry.dataloader import DataLoader
from database import models
from graphql_schema.dataloaders.base import SingleModelByIdDataloader


def create_dataloader(model: Type[models.BaseModel], relationship_column=None, filters: Optional[list] = None):
    loader = SingleModelByIdDataloader(model, relationship_column, filters).load
    return DataLoader(load_fn=loader, cache=False)


airport_dataloader = create_dataloader(models.Airport)
aircraft_dataloader = create_dataloader(models.Aircraft)
event_dataloader = create_dataloader(models.Event)
organizations_dataloader = create_dataloader(models.Organization)
airport_weather_info_loader = create_dataloader(models.WeatherInfo)
poi_dataloader = create_dataloader(models.PointOfInterest)
poi_type_dataloader = create_dataloader(models.PointOfInterestType)

cover_photo_loader = create_dataloader(
    models.Photo,
    relationship_column=models.Photo.flight_id,
    filters=[models.Photo.is_flight_cover.is_(True)]
)
