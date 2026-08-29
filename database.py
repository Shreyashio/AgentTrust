"""
Database connection and session setup using SQLite and SQLAlchemy.
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import config

# Connect to SQLite database file
engine = create_engine(
    config.DATABASE_URL,
    connect_args={"check_same_thread": False}  # Needed for SQLite in multi-threaded FastAPI
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """FastAPI dependency that provides a database session and closes it on completion."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
