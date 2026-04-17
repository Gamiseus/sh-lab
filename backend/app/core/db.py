import os
from sqlmodel import create_engine, SQLModel, Session
from app.core.config import settings

# Create database engine
# echo=True logs all SQL queries — only enable in development
engine = create_engine(settings.DATABASE_URL, echo=os.getenv("SQL_ECHO", "").lower() == "true")

def init_db():
    """Example init db function to create tables if they don't exist"""
    from app import models
    SQLModel.metadata.create_all(engine)

def get_session():
    """Dependency to get a DB session"""
    with Session(engine) as session:
        yield session
