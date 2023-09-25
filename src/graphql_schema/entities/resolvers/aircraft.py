from operator import or_
from typing import Set, Optional
from database import models
from graphql_schema.entities.resolvers.base import get_base_resolver


def get_aircraft_resolver(user_id: int, organization_ids: Optional[Set[int]] = None, aircraft_id: Optional[int] = None):
    query = get_base_resolver(
        model=models.Aircraft,
        order_by=[models.Aircraft.id.desc()],
        object_id=aircraft_id,
        user_id=user_id if not organization_ids else None
    )
    if organization_ids:
        query = (
            query.filter(
                or_(
                    models.Aircraft.created_by_id == user_id,
                    models.Aircraft.organization_id.in_(organization_ids)
                )
            )
        )

    return query