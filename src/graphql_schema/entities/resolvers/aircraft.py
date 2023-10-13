from operator import or_
from typing import Set, Optional
from database import models
from graphql_schema.entities.resolvers.base import BaseMutationResolver, BaseQueryResolver
from graphql_schema.entities.types.types import Aircraft


class AircraftQueryResolver(BaseQueryResolver):
    def __init__(self):
        super().__init__(graphql_type=Aircraft, model=models.Aircraft)

    def get_query(
            self,
            user_id: Optional[int] = None,
            object_id: Optional[int] = None,
            order_by: Optional[list] = None,
            organization_ids: Optional[Set[int]] = None,
            *args,
            **kwargs,
    ):
        query = super().get_query(
            order_by=[models.Aircraft.id.desc()],
            object_id=object_id,
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


class AircraftMutationResolver(BaseMutationResolver):
    def __init__(self):
        super().__init__(graphql_type=Aircraft, model=models.Aircraft)
