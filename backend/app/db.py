from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url, pool_pre_ping=True,
                       pool_size=settings.database_pool_size,
                       max_overflow=settings.database_max_overflow,
                       pool_timeout=10, pool_recycle=300,
                       connect_args={"connect_timeout": 10})
Session = sessionmaker(engine, expire_on_commit=False)


def get_db():
    with Session() as session:
        yield session
