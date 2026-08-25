import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DB_URL = os.environ.get("VINYL_API_DATABASE_URL", "sqlite:///./vinyl_api_dev.db")

engine = create_engine(DB_URL, connect_args={"check_same_thread": False} if "sqlite" in DB_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def init_db():
    # import models to register them with Base before creating tables
    from . import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
