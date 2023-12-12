from typing import TypeVar, Generic, List
import strawberry
from sqlalchemy import func, Select
from database.transaction import get_session

Item = TypeVar("Item")


@strawberry.type
class PaginationWindow(Generic[Item]):
    items: List[Item] = strawberry.field(
        description="The list of items in this pagination window."
    )

    total_items_count: int = strawberry.field(
        description="Total number of items in the filtered dataset."
    )


async def get_pagination_window(
        query: Select,
        item_type: type,
        limit: int,
        offset: int = 0,
) -> PaginationWindow:
    if limit <= 0:
        raise Exception(f"limit ({limit}) must be > 0")

    async with get_session() as db:
        cnt_query = query.with_only_columns(func.count())
        total_items_count = (await db.scalars(cnt_query)).one()

    # if offset != 0 and not 0 <= offset < total_items_count:
    #     raise Exception(f"offset ({offset}) is out of range " f"(0-{total_items_count - 1})")

    async with get_session() as db:
        data = (await db.scalars(query.limit(limit).offset(offset))).all()
        dataset = [item_type(**i.as_dict()) for i in data]

    return PaginationWindow(
        items=dataset,
        total_items_count=total_items_count
    )
