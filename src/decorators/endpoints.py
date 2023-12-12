from functools import wraps
from fastapi import HTTPException
from starlette.status import HTTP_401_UNAUTHORIZED


def allow_public(func):
    @wraps(func)
    async def decorator(*args, **kwargs):
        if 'info' in kwargs:
            user_id = kwargs['info'].context.user_id
            public = kwargs.get('public')
            if not user_id and not public:
                raise HTTPException(HTTP_401_UNAUTHORIZED)

            return await func(*args, **kwargs)

    return decorator


def authenticated_user_only(raise_when_unauthorized: bool = True, return_value_unauthorized=None):
    def wrapper(func):
        @wraps(func)
        async def decorator(*args, **kwargs):
            if 'info' in kwargs:
                if not kwargs['info'].context.user_id:
                    if raise_when_unauthorized:
                        raise HTTPException(HTTP_401_UNAUTHORIZED, "Not authorized")
                    else:
                        return return_value_unauthorized
            return await func(*args, **kwargs)

        return decorator

    return wrapper
