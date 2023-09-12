import asyncio
import functools
from typing import Callable

from database import async_session


def transactional(func: Callable) -> Callable:
    @functools.wraps(func)
    async def _wrapper(*args, **kwargs):
        # db_session = db_session_context.get()
        # if db_session:
        #     return func(*args, **kwargs)

        db_session = async_session()

        print("STARTUJI TRANSAKCI")
        db_session.begin()
        # db_session_context.set(db_session)
        try:
            kwargs['db'] = db_session
            result = await func(*args, **kwargs)
            await db_session.commit()
            print("KONEC TRANSAKCE V DEKORATORU")

        except Exception as e:
            await db_session.rollback()
            raise

        finally:
            await db_session.close()
            # db_session_context.set(None)
        return result

    return _wrapper