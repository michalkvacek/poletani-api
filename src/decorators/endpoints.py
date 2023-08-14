from functools import wraps
from fastapi import HTTPException
from starlette.status import HTTP_401_UNAUTHORIZED


def public_endpoint(func):
    pass


def authenticated_user_only(func):
    @wraps(func)
    async def decorator(*args, **kwargs):
        if 'info' in kwargs:
            if not kwargs['info'].context.user_id:
                raise HTTPException(HTTP_401_UNAUTHORIZED, "Not authorized")

        return await func(*args, **kwargs)

    return decorator
