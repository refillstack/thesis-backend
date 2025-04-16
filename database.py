from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os
from dotenv import load_dotenv

load_dotenv()

# Get database URL from environment variable
DATABASE_URL = os.getenv("DATABASE_URL")

# If DATABASE_URL is not set or contains placeholder values, use SQLite
if not DATABASE_URL or "[YOUR-PROJECT-REF]" in DATABASE_URL:
    print("Warning: Using SQLite database for local development")
    DATABASE_URL = "sqlite:///./thesis.db"

engine = create_engine(DATABASE_URL, connect_args={} if DATABASE_URL.startswith("postgresql") else {"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 