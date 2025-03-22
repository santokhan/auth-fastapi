import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import HTTPException
from pymongo import database

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME")

client = None


async def connect_mongo():
    global client
    try:
        client = AsyncIOMotorClient(MONGO_URI)
        print("Connected to: ", client)
        return client
    except EnvironmentError as e:
        raise HTTPException(500, str(e))


async def get_db() -> database:
    try:
        return client[DB_NAME]
    except Exception as e:
        print(e)
        raise HTTPException(500, str(e))
