import typing
from typing import List, Optional
import strawberry
from sqlalchemy import inspect
from database.models import BaseModel


def get_annotations_for_scalars(model: BaseModel, exclude_fields=None, force_optional: bool = False):
    if exclude_fields is None:
        exclude_fields = []

    annotations_ = {}
    for name, column in inspect(model).columns.items():
        is_optional = column.nullable or force_optional
        if name in exclude_fields:
            continue
        annotations_[name] = column.type.python_type if not is_optional else typing.Optional[column.type.python_type]

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

    ignored_fields = ["created_at", "created_by_id", "updated_by_id", "updated_at", "deleted"]

    def wrapper(cls):
        cls.__annotations__.update(get_annotations_for_scalars(
            model,
            exclude_fields=exclude_fields + ignored_fields,
            force_optional=all_optional
        ))
        return strawberry.input(cls)

    return wrapper
