from typing import Type, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from database import models
from graphql_schema.entities.types.mutation_input import ComboboxInput


async def handle_combobox_save(
        db: AsyncSession,
        model: Type[models.BaseModel],
        input: ComboboxInput,
        user_id: int,
        name_column: str = "name",
        extra_data: Optional[dict] = None
) -> int:
    if input.id:
        return input.id
    else:

        if not extra_data:
            extra_data = {}

        data = {name_column: input.name, **extra_data}
        if hasattr(model, "created_by_id"):
            data["created_by_id"] = user_id

        obj = await model.create(db, data)
        await db.flush()
        return obj.id
