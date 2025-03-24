from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api.v1 import root
from app.utils.cors import allow_origins
from db import create_tables
from app.api.v1.users import auth
from app.api.v1.users import users
from app.api.v1 import profile
import debugpy
from dotenv import load_dotenv
from os import getenv

load_dotenv()

if getenv("DEBUG"):
    debugpy.listen(("0.0.0.0", 5678))


def create_app():
    create_tables()

    app = FastAPI(title="Authentication")

    app.mount("/static", StaticFiles(directory="static"), name="static")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(prefix="/v1", router=auth.router)
    app.include_router(prefix="/v1", router=users.router)
    app.include_router(prefix="/v1", router=profile.router)

    # Serve static files from the "uploads" folder
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

    return app


app = create_app()
