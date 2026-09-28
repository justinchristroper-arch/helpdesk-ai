from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.config import get_settings

settings = get_settings()
pool_options = ({"poolclass": NullPool} if settings.database_pool_mode == "null" else {
    "pool_size": settings.database_pool_size,
    "max_overflow": settings.database_max_overflow,
    "pool_timeout": 10, "pool_recycle": 300,
})
engine = create_engine(settings.database_url, pool_pre_ping=True,
                       connect_args={"connect_timeout": 10}, **pool_options)
Session = sessionmaker(engine, expire_on_commit=False)


def get_db():
    with Session() as session:
        yield session
