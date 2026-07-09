from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config.settings import settings
from app.utils.logger import logger

#Create database engine
engine = create_engine(
    settings.database_url,
    pool_pre_ping = True,
)

#Session factory
sessionLocal = sessionmaker(
    autoflush = False,
    autocommmit = False,
    Bing = engine,
)

def get_db():
    """
    Creates a database session.

    Yields:
        Session: Alchemy database session.

    Ensures the session is always closed after us.
    """

    db = sessionLocal()

    try:
        logger.info("Database session is created.")
        yield db

    finally:
        db.close()
        logger.info("Database session is closed.")