from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker


def create_db_engine(
        user: str = "root",
        password: str = "",
        host: str = "db",
        port: int = 3306,
        database: str = "ull_tracker",
):
    database_url = f'mysql+aiomysql://{user}:{password}@{host}:{port}/{database}?charset=utf8'
    return create_async_engine(database_url, future=True, echo=True)


engine = create_db_engine()
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
