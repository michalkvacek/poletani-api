from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from database import async_session


@asynccontextmanager
async def get_session():
    async with async_session() as session:
        async with session.begin():
            try:
                yield session
                await session.commit()
            except:
                await session.rollback()
                raise
            finally:
                session.expunge_all()
                await session.close()


async def db_session():
    async with async_session() as session:
        async with session.begin():
            yield session
            await session.flush()
            await session.commit()
            print("CCCCCCCCCCCCCOOOOOOOOOOOOOOMMMMMMMMMMIIIIIIIIIIIITTTTTTTTTTTT")
