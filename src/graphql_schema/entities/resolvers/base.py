from typing import Optional, Type, TypeVar, Generic, List
from sqlalchemy.ext.asyncio import AsyncSession
from database import models
from database.query_builder import QueryBuilder
from database.transaction import get_session
from graphql_schema.entities.types.base import BaseGraphqlInputType

GQL_TYPE = TypeVar('GQL_TYPE')


class BaseResolver(Generic[GQL_TYPE]):
    def __init__(self, graphql_type: GQL_TYPE, model: Type[models.BaseModel]):
        self.graphql_type = graphql_type
        self.model = model
        self.query_builder = QueryBuilder(self.model)


class BaseQueryResolver(BaseResolver):
    async def _get_list(self, query) -> List[GQL_TYPE]:
        async with get_session() as db:
            items = (await db.scalars(query)).all()

            return [self.graphql_type(**m.as_dict()) for m in items]

    async def _get_one(self, query) -> GQL_TYPE:
        async with get_session() as db:
            data = (await db.scalars(query)).one()
            return self.graphql_type(**data.as_dict())

    def get_query(
            self,
            user_id: Optional[int] = None,
            object_id: Optional[int] = None,
            order_by: Optional[list] = None,
            only_public: Optional[bool] = False,
            **kwargs,
    ):
        query = self.query_builder.get_simple_query(created_by_id=user_id, order_by=order_by, only_public=only_public)

        if object_id:
            if not hasattr(self.model, "id"):
                raise AssertionError(f"Model {self.model} has no ID column! Cannot query by ID!")
            query = query.filter(self.model.id == object_id)

        if kwargs:
            query = query.filter_by(**kwargs)

        return query

    async def get_list(self, user_id: Optional[int] = None, **kwargs) -> List[GQL_TYPE]:
        query = self.get_query(user_id, **kwargs)
        return await self._get_list(query)

    async def get_one(self, user_id: Optional[int] = None, **kwargs) -> GQL_TYPE:
        query = self.get_query(user_id, **kwargs)
        return await self._get_one(query)


class BaseMutationResolver(BaseResolver):
    async def _get_one(self, db: AsyncSession, id: int, created_by_id: int) -> models.BaseModel:
        query = self.query_builder.get_simple_query(created_by_id=created_by_id).filter(self.model.id == id)
        return (await db.scalars(query)).one()

    async def _do_create(self, db: AsyncSession, data: dict) -> GQL_TYPE:
        model = await self.model.create(db, data=data)
        return self.graphql_type(**model.as_dict())

    async def _do_update(self, db: AsyncSession, obj: models.BaseModel | dict | int, data: dict) -> GQL_TYPE:
        update_where = {}
        if isinstance(obj, models.BaseModel):
            update_where['obj'] = obj
        elif isinstance(obj, dict):
            update_where['id'] = obj['id']
        else:
            update_where['id'] = obj

        model = await self.model.update(db, data=data, **update_where)
        return self.graphql_type(**model.as_dict())

    async def create(self, context, data: BaseGraphqlInputType) -> GQL_TYPE:
        input_data = data.to_dict()

        if hasattr(self.model, "created_by_id"):
            input_data['created_by_id'] = context.user_id

        async with get_session() as db:
            return await self._do_create(db, input_data)

    async def update(self, id: int, data: BaseGraphqlInputType, user_id: int) -> GQL_TYPE:
        async with get_session() as db:
            item = await self._get_one(db, id, user_id)
            return await self._do_update(db, item, data.to_dict())

    async def delete(self, user_id: int, id: int) -> GQL_TYPE:
        async with get_session() as db:
            model = await self._get_one(db, id, user_id)

            if hasattr(self.model, "deleted"):
                model = await self.model.update(db, obj=model, data=dict(deleted=True))
            else:
                await db.delete(model)

            return self.graphql_type(**model.as_dict())

