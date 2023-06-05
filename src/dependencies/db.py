from database import async_session


async def db_session():
    async with async_session() as session:
        async with session.begin():
            yield session
