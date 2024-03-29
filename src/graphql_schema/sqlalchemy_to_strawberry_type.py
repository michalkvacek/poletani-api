import typing
from typing import List, Optional
import strawberry
import sqlalchemy
from sqlalchemy import Column
from logger import log
from database.models import BaseModel
from graphql_schema.entities.types.base import BaseGraphqlInputType


def get_columns_from_model(model: BaseModel, exclude_fields: List[str]) -> List[typing.Tuple[str, Column]]:
    return [(name, column) for name, column in sqlalchemy.inspect(model).columns.items() if name not in exclude_fields]


def get_annotations_for_scalars(model: BaseModel, exclude_fields=None, force_optional: bool = False):
    if exclude_fields is None:
        exclude_fields = []

    annotations_ = {}
    for name, column in get_columns_from_model(model, exclude_fields):
        is_optional = column.nullable or force_optional
        try:
            type_ = typing.Optional[column.type.python_type] if is_optional else column.type.python_type
            annotations_[name] = type_
        except NotImplementedError as e:
            log.warning(f"Cannot annotate {name} in {model} for GQL type. Exception: {e}")

    return annotations_


def strawberry_sqlalchemy_type(model, exclude_fields: Optional[typing.Union[List, typing.Tuple]] = None):
    if exclude_fields is None:
        exclude_fields = []

    def from_sqlalchemy_model(cls, model: BaseModel):
        return cls(model)

    def wrapper(cls):
        cls.__annotations__.update(get_annotations_for_scalars(model, exclude_fields=exclude_fields + ["deleted"]))
        cls.from_sqlalchemy_model = from_sqlalchemy_model
        return strawberry.type(cls)

    return wrapper


def strawberry_sqlalchemy_input(
        model,
        exclude_fields: Optional[typing.Union[List, typing.Tuple]] = None,
        all_optional: bool = False) -> typing.Callable[[...], strawberry.object_type]:
    if exclude_fields is None:
        exclude_fields = []

    ignored_fields = exclude_fields + BaseGraphqlInputType.base_ignored_fields

    def wrapper(cls):
        annotations = get_annotations_for_scalars(
            model,
            exclude_fields=ignored_fields,
            force_optional=all_optional
        )

        cls.__annotations__.update(annotations)

        for col, col_type in annotations.items():
            try:
                if col_type._name == 'Optional':  # noqa
                    setattr(cls, col, None)
            except AttributeError:
                pass

        input_cls = strawberry.input(cls)

        return input_cls

    return wrapper
