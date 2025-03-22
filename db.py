from dotenv import load_dotenv
from sqlalchemy import create_engine
from os import getenv
from sqlalchemy.orm import sessionmaker
from models import Base
import aioredis

load_dotenv()

DATABASE_URL = getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_tables():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Redis connection pool
async def get_redis():
    redis = await aioredis.from_url("redis://redis:6379", decode_responses=True)
    try:
        yield redis
    finally:
        await redis.close()
