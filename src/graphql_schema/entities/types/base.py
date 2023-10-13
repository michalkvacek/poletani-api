from datetime import datetime
from typing import List


class BaseGraphqlInputType:
    base_ignored_fields: List[str] = ["created_at", "created_by_id", "updated_by_id", "updated_at", "deleted"]
    ignored_fields: List[str] = []

    def to_dict(self) -> dict:
        dict_data = {}
        for key in self.__annotations__.keys():
            value = getattr(self, key)
            if value is None or key in self.ignored_fields + self.base_ignored_fields:
                continue

            if isinstance(value, datetime):
                value = value.astimezone()

            dict_data[key] = value

        return dict_data
