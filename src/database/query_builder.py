from typing import Optional, Type
from sqlalchemy import select, or_
from database import models


class QueryBuilder:
    def __init__(self, model: Type[models.BaseModel]):
        self.model = model

    def get_simple_query(
            self,
            extra_select: Optional[list] = None,
            created_by_id: Optional[int] = None,
            order_by: Optional[list] = None,
            include_deleted: bool = False
    ):
        if not extra_select:
            extra_select = []

        query = select(self.model, *extra_select)

        if not include_deleted and hasattr(self.model, "deleted"):
            query = query.filter(self.model.deleted.is_(False))

        if hasattr(self.model, "created_by_id") and created_by_id:
            query = query.filter(self.model.created_by_id == created_by_id)

        if order_by:
            query = query.order_by(*order_by)

        return query
