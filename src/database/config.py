import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker


def get_database_url():
    user = os.environ.get("MYSQL_USER", "root")
    password = os.environ.get("MYSQL_PASSWORD", "")
    host = os.environ.get("MYSQL_HOST", "db")
    port = int(os.environ.get("MYSQL_PORT", 3306))
    database = os.environ.get("MYSQL_DATABASE", "ull_tracker")

    return f'mysql+aiomysql://{user}:{password}@{host}:{port}/{database}?charset=utf8'


def create_db_engine():
    database_url = get_database_url()
    return create_async_engine(database_url, future=True, echo=True, pool_pre_ping=True)


engine = create_db_engine()
async_session = async_sessionmaker(engine, expire_on_commit=True, class_=AsyncSession)
