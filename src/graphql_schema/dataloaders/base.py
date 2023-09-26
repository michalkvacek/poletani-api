from collections import defaultdict
from sqlalchemy import select
from typing import Type, List, Optional
from database import models, async_session


class SingleModelByIdDataloader:
    def __init__(
            self, model: Type[models.BaseModel], relationship_column=None, filters: Optional[list] = None
    ) -> None:
        super().__init__()
        self.model = model
        self.relationship_column = relationship_column if relationship_column else model.id

        if filters is None:
            filters = []
        self.filters = filters

    async def load(self, ids: List[int]):
        async with async_session() as session:
            query = select(self.model, self.relationship_column).filter(self.relationship_column.in_(ids))
            for filter_ in self.filters:
                query = query.filter(filter_)

            items = (await session.execute(query)).all()
            items_by_id = {rel_id: item for item, rel_id in items}
            return [items_by_id.get(id_) for id_ in ids]


class MultiModelsDataloader:
    def __init__(
            self,
            model: Type[models.BaseModel],
            relationship_column,
            extra_join: Optional[list] = None,
            filters: Optional[list] = None,
            order_by: Optional[list] = None,
    ):
        if extra_join is None:
            extra_join = []

        if filters is None:
            filters = []

        if order_by is None:
            order_by = [model.id.desc()]  # defaultne radit od nejnovejsich zaznamu

        self.model = model
        self.relationship_column = relationship_column
        self.extra_join = extra_join
        self.order_by = order_by
        self.filters = filters

    async def load(self, ids: List[int]):
        async with async_session() as session:
            rel_column = self.relationship_column
            query = (
                select(self.model, rel_column)
                .filter(rel_column.in_(ids))
                .order_by(*self.order_by)
            )

            for table in self.extra_join:
                query = query.join(table)

            for filter_ in self.filters:
                query = query.filter(filter_)

            data = (await session.execute(query)).all()

            result_data = defaultdict(list)
            for item, rel_id in data:
                result_data[rel_id].append(item)

            return [result_data[id_] for id_ in ids]
