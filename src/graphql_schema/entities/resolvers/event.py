from typing import Optional
from database import models
from graphql_schema.entities.resolvers.base import BaseQueryResolver
from graphql_schema.entities.types.types import Event


class EventQueryResolver(BaseQueryResolver):
    def __init__(self):
        super().__init__(graphql_type=Event, model=models.Event)

    def get_query(
            self,
            user_id: Optional[int] = None,
            object_id: Optional[int] = None,
            order_by: Optional[list] = None,
            only_public: Optional[bool] = True,
            *args,
            **kwargs,
    ):
        query = super().get_query(
            user_id, object_id,
            order_by=[models.Event.date_from.desc()],
            only_public=not bool(user_id)
        )

        if kwargs.get('username'):
            query = (
                query
                .join(models.Event.created_by)
                .filter(models.User.public_username == kwargs['username'])
            )

        return query
