from typing import Optional
from graphql import GraphQLError


def get_detail_filters(id: Optional[int], url_slug: Optional[str]) -> dict:
    filter_params = {}
    if id:
        filter_params['object_id'] = id
    if url_slug is not None:
        filter_params['url_slug'] = url_slug

    if not filter_params:
        raise GraphQLError("You must specifiy either urlSlug or id!")

    return filter_params
