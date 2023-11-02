from typing import Optional
from database import models
from graphql_schema.entities.resolvers.base import BaseQueryResolver
from graphql_schema.entities.types.types import Copilot


class CopilotQueryResolver(BaseQueryResolver):
    def __init__(self):
        super().__init__(Copilot, models.Copilot)

    def get_query(
            self,
            user_id: Optional[int] = None,
            object_id: Optional[int] = None,
            order_by: Optional[list] = None,
            only_public: Optional[bool] = False,
            *args, **kwargs
    ):
        query = super().get_query(user_id, object_id, order_by, only_public, *args, **kwargs)

        if kwargs.get("pilot_username"):
            query = (
                query.join(models.Copilot.created_by)
                .filter(models.User.public_username == kwargs['pilot_username'])
            )

        return query
