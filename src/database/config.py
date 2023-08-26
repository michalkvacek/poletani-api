import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker


def get_database_url():
    user = os.environ.get("MYSQL_USER", "root")
    password = os.environ.get("MYSQL_PASSWORD", "")
    host = os.environ.get("MYSQL_HOST", "db")
    port = int(os.environ.get("MYSQL_PORT", 3306))
    database = os.environ.get("MYSQL_DATABASE", "ull_tracker")

    return f'mysql+aiomysql://{user}:{password}@{host}:{port}/{database}?charset=utf8'


def create_db_engine():
    database_url = get_database_url()
    return create_async_engine(database_url, future=True, echo=True)


engine = create_db_engine()
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
