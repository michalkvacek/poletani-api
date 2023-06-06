import typing
from typing import List, Optional
import strawberry
import sqlalchemy
from sqlalchemy import Column
from database.models import BaseModel


def get_columns_from_model(model: BaseModel, exclude_fields: List[str]) -> List[typing.Tuple[str, Column]]:
    return [(name, column) for name, column in sqlalchemy.inspect(model).columns.items() if name not in exclude_fields]


def get_annotations_for_scalars(model: BaseModel, exclude_fields=None, force_optional: bool = False):
    if exclude_fields is None:
        exclude_fields = []

    annotations_ = {}
    for name, column in get_columns_from_model(model, exclude_fields):
        is_optional = column.nullable or force_optional
        try:
            annotations_[name] = column.type.python_type if not is_optional else typing.Optional[column.type.python_type]
        except NotImplementedError as e:
            print(f"Neimplementovano: {e}, {name=}")

    return annotations_


def strawberry_sqlalchemy_type(model, exclude_fields: Optional[typing.Union[List, typing.Tuple]] = None):
    if exclude_fields is None:
        exclude_fields = []

    def from_sqlalchemy_model(model: BaseModel):
        return model

    def wrapper(cls):
        cls.__annotations__.update(get_annotations_for_scalars(model, exclude_fields=exclude_fields + ["deleted"]))
        cls.from_sqlalchemy_model = from_sqlalchemy_model
        return strawberry.type(cls)

    return wrapper


def strawberry_sqlalchemy_input(
        model,
        exclude_fields: Optional[typing.Union[List, typing.Tuple]] = None,
        all_optional: bool = False):
    if exclude_fields is None:
        exclude_fields = []

    ignored_fields = exclude_fields + ["created_at", "created_by_id", "updated_by_id", "updated_at", "deleted"]

    def to_dict(self):
        return {name: getattr(self, name) for name, _ in get_columns_from_model(model, ignored_fields)}

    def wrapper(cls):
        cls.__annotations__.update(get_annotations_for_scalars(
            model,
            exclude_fields=ignored_fields,
            force_optional=all_optional
        ))
        cls.to_dict = to_dict
        return strawberry.input(cls)

    return wrapper
