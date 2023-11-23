from collections import defaultdict
from typing import Type, List, Optional
from database import models, async_session
from database.query_builder import QueryBuilder


class BaseDataloader:
    def __init__(
            self,
            model: Type[models.BaseModel],
            relationship_column, filters: Optional[list] = None
    ) -> None:
        super().__init__()
        self.model = model
        self.query_builder = QueryBuilder(self.model)

        if relationship_column is None:
            relationship_column = model.id
        self.relationship_column = relationship_column

        if filters is None:
            filters = []
        self.filters = filters


class SingleModelByIdDataloader(BaseDataloader):
    async def load(self, ids: List[int]):
        async with async_session() as session:
            query = (
                self.query_builder.get_simple_query(extra_select=[self.relationship_column], include_deleted=True)
                .filter(self.relationship_column.in_(set(ids)))
                .filter(*self.filters)
            )

            items = (await session.execute(query)).all()
            items_by_id = {rel_id: item for item, rel_id in items}
            return [items_by_id.get(id_) for id_ in ids]


class MultiModelsDataloader(BaseDataloader):
    def __init__(
            self,
            model: Type[models.BaseModel],
            relationship_column=None,
            filters: Optional[list] = None,
            extra_join: Optional[list] = None,
            order_by: Optional[list] = None,
    ):
        super().__init__(model, relationship_column, filters)

        if extra_join is None:
            extra_join = []
        self.extra_join = extra_join

        if order_by is None:
            order_by = [model.id.desc()]  # defaultne radit od nejnovejsich zaznamu
        self.order_by = order_by

    async def load(self, ids: List[int]):
        async with async_session() as db:
            query = (
                self.query_builder.get_simple_query(
                    extra_select=[self.relationship_column],
                    order_by=self.order_by
                )
                .filter(self.relationship_column.in_(set(ids)))
                .filter(*self.filters)
            )

            for joined_table in self.extra_join:
                query = query.join(joined_table)

            if self.filters:
                query = query.filter(*self.filters)

            data = (await db.execute(query)).all()

            result_data = defaultdict(list)
            for item, rel_id in data:
                result_data[rel_id].append(item)

            return [result_data[id_] for id_ in ids]
