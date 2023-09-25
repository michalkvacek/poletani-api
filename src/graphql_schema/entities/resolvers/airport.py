from typing import Optional
from sqlalchemy import or_
from database import models
from graphql_schema.entities.resolvers.base import get_base_resolver


def get_airport_resolver(user_id: int, airport_id: Optional[int] = None):
    if airport_id:
        return get_base_resolver(model=models.Airport, object_id=airport_id, user_id=user_id)

    return (
        get_base_resolver(model=models.Airport)
        .filter(or_(
            models.Airport.created_by_id == user_id,
            models.Airport.created_by_id.is_(None),
        ))
    )