from functools import wraps
from graphql import GraphQLError


def error_logging(func):
    @wraps(func)
    async def decorator(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            raise GraphQLError(f"Not found")

    return decorator
