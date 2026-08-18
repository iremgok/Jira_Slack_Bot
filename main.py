from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.database.base import Base
from app.database.db import engine
from app.scheduler.scheduler import SchedulerServices
from app.utils.logger import logger
from app.api.routes import router

# Initialize scheduler
scheduler = SchedulerServices()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles application startup and shutdown events.
    """
    logger.info("Initializing database tables...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database tables: {e}")

    logger.info("Starting background scheduler...")
    try:
        scheduler.start()
        logger.info("Background scheduler started successfully.")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")

    yield

    logger.info("Shutting down background scheduler...")
    try:
        scheduler.shutdown()
        logger.info("Background scheduler stopped successfully.")
    except Exception as e:
        logger.error(f"Failed to stop scheduler: {e}")


app = FastAPI(
    title="Jira Slack Bot",
    version="1.0.0",
    lifespan=lifespan,
)

# Include API routes
app.include_router(router)


def main() -> None:
    """
    Application entry point for running locally.
    """
    import uvicorn
    logger.info("Starting FastAPI server...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()
