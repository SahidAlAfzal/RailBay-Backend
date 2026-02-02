from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

load_dotenv()
#from app.config import settings
# 1. Get the URL (Try 'DATABASE_URL' first for Cloud, then 'SQLALCHEMY_DATABASE_URL' for Local)
database_url = os.getenv("DATABASE_URL") or os.getenv("SQLALCHEMY_DATABASE_URL")

# 2. Fallback for safety (prevents crashing if both are missing, though it won't connect)
if not database_url:
    database_url = "postgresql://postgres:password@localhost:5433/postgres"

# 3. Fix "postgres://" bug (Railway often sends 'postgres://' but SQLAlchemy needs 'postgresql://')
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

SQLALCHEMY_DATABASE_URL = database_url

engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autoflush=False,autocommit=False,bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()