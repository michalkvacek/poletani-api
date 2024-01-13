from operator import or_
from typing import Set, Optional
from database import models
from database.transaction import get_session
from graphql_schema.entities.helpers.combobox import handle_combobox_save
from graphql_schema.entities.resolvers.base import BaseMutationResolver, BaseQueryResolver
from graphql_schema.entities.types.mutation_input import EditAircraftInput, CreateAircraftInput
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
        call_sign = kwargs.get("call_sign")
        filters = {}
        if object_id:
            filters['object_id'] = object_id
        if call_sign:
            filters['call_sign'] = call_sign

        query = super().get_query(
            order_by=[models.Aircraft.id.desc()],
            user_id=user_id if not organization_ids else None,
            **filters
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

    async def create(self, context, data: CreateAircraftInput) -> Aircraft:
        input_data = data.to_dict()

        async with get_session() as db:
            input_data['created_by_id'] = context.user_id
            if data.organization:
                input_data['organization_id'] = await handle_combobox_save(
                    db,
                    models.Organization,
                    input=data.organization,
                    user_id=context.user_id,
                )

            return await self._do_create(db, data=input_data)

    async def update(self, id: int, user_id: int, data: EditAircraftInput) -> Aircraft:
        update_data = data.to_dict()
        async with get_session() as db:
            if data.organization:
                update_data['organization_id'] = await handle_combobox_save(
                    db,
                    models.Organization,
                    input=data.organization,
                    user_id=user_id,
                )

            return await self._do_update(db, id, update_data)
