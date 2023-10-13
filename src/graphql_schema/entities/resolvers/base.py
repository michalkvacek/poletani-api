from typing import Optional, Type, T
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from database import models
from database.transaction import get_session


class BaseQueryResolver:

    def __init__(self, graphql_type, model):
        self.graphql_type = graphql_type
        self.model = model

    def get_query(
            self,
            user_id: Optional[int] = None,
            object_id: Optional[int] = None,
            order_by: Optional[list] = None,
            include_public: Optional[bool] = True,
            *args,
            **kwargs,
    ):
        query = select(self.model)

        if object_id:
            if hasattr(self.model, "id"):
                query = query.filter(self.model.id == object_id)
            else:
                raise AssertionError(f"Model {self.model} has no ID column! Cannot query by ID!")

        if hasattr(self.model, "deleted"):
            query = query.filter(self.model.deleted.is_(False))

        ownership_clause = []
        if hasattr(self.model, "is_public") and include_public:
            ownership_clause.append(self.model.is_public.is_(True))

        if hasattr(self.model, "created_by_id") and user_id:
            ownership_clause.append(self.model.created_by_id == user_id)

        if len(ownership_clause) > 1:
            query = query.filter(or_(*ownership_clause))
        elif len(ownership_clause) == 1:
            query = query.filter(*ownership_clause)

        if order_by:
            query = query.order_by(*order_by)

        return query

    async def _get_list(self, query):
        async with get_session() as db:
            items = (await db.scalars(query)).all()

            return [self.model(**m.as_dict()) for m in items]

    async def _get_one(self, query):
        async with get_session() as db:
            data = (await db.scalars(query)).one()
            return self.model(**data.as_dict())

    async def get_list(self, user_id: Optional[int] = None, **kwargs) -> list:
        query = self.get_query(user_id, **kwargs)
        return await self._get_list(query)

    async def get_one(self, id: int, user_id: Optional[int] = None, **kwargs):
        query = self.get_query(user_id, object_id=id, **kwargs)
        return await self._get_one(query)


class BaseMutationResolver:
    model: Type[models.BaseModel]
    graphql_type: Type[T] = None

    def __init__(self, graphql_type: Type[T], model: Type[models.BaseModel]):
        self.graphql_type = graphql_type
        self.model = model

    async def delete(self, user_id: int, id: int) -> T:
        async with get_session() as db:
            query = BaseQueryResolver(self.graphql_type, self.model).get_query(user_id, object_id=id)
            model = (await db.scalars(query)).one()

            if hasattr(self.model, "deleted"):
                model = await self.model.update(db, obj=model, data=dict(deleted=True))
            else:
                await db.delete(model)

            return self.graphql_type(**model.as_dict())

    async def create(self, data: dict, user_id: Optional[int] = None) -> T:
        input_data = {**data}
        if hasattr(self.model, "created_by_id"):
            input_data['created_by_id'] = user_id

        async with get_session() as db:
            model = await self.model.create(db, data=input_data)
            return self.graphql_type(**model.as_dict())

    async def _do_update(self, db: AsyncSession, obj: models.BaseModel | dict, data: dict) -> T:
        update_where = {}
        if isinstance(obj, models.BaseModel):
            update_where['obj'] = obj
        else:
            update_where['id'] = obj['id']

        model = await self.model.update(db, data=data, **update_where)
        return self.graphql_type(**model.as_dict())
