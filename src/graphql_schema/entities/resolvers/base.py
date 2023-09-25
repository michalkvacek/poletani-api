from typing import Optional, Type
from sqlalchemy import select, or_
from database import models
from dependencies.db import get_session


def get_base_resolver(
        model: Type[models.BaseModel],
        object_id: Optional[int] = None,
        user_id: Optional[int] = None,
        order_by: Optional[list] = None,
        include_public: Optional[bool] = True,
):
    query = select(model)

    if object_id:
        if hasattr(model, "id"):
            query = query.filter(model.id == object_id)
        else:
            raise AssertionError(f"Model {model} has no ID column! Cannot query by ID!")

    if hasattr(model, "deleted"):
        query = query.filter(model.deleted.is_(False))

    ownership_clause = []
    if hasattr(model, "is_public") and include_public:
        ownership_clause.append(model.is_public.is_(True))

    if hasattr(model, "created_by_id") and user_id:
        ownership_clause.append(model.created_by_id == user_id)

    if len(ownership_clause) > 1:
        query = query.filter(or_(*ownership_clause))
    elif len(ownership_clause) == 1:
        query = query.filter(*ownership_clause)

    if order_by:
        query = query.order_by(*order_by)

    return query


async def get_list(model, query):
    async with get_session() as db:
        items = (await db.scalars(query)).all()

        return [model(**m.as_dict()) for m in items]


async def get_one(model, query):
    async with get_session() as db:
        data = (await db.scalars(query)).one()
        return model(**data.as_dict())
