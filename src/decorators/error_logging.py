from functools import wraps
from fastapi import HTTPException
from graphql import GraphQLError
from sqlalchemy.exc import NoResultFound


def error_logging(func):
    @wraps(func)
    async def decorator(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except NoResultFound as e:
            raise GraphQLError("Not found", original_error=e)
        except HTTPException as e:
            if e.status_code == 401:
                raise GraphQLError("Not authorized", original_error=e)

    return decorator
