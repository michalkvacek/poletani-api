from contextlib import asynccontextmanager
from database import async_session


@asynccontextmanager
async def get_session():
    async with async_session() as session:
        async with session.begin():
            try:
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                print(f"ERROR: {e}")
                raise
            finally:
                session.expunge_all()
                await session.close()
