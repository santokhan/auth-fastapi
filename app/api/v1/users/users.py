from fastapi import Depends, HTTPException, APIRouter, Path
from db import get_db
from schemas.user import UserOut, UsersOut
from sqlalchemy.orm import Session
from models import Users
from db import get_redis
from aioredis.client import Redis
from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials,
)
from app.api.v1.users.helper.bearer import get_bearer_token
from json import dumps
from .helper.token import decode

router = APIRouter(tags=["users"])


@router.get("/users", description="Only admin can access this route")
async def get_users(
    # header=Depends(HTTPBearer()),
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> UsersOut:
    try:
        users = db.query(Users).all()

        filtered = []

        for user in users:
            filtered.append(
                UserOut(
                    id=user.id,
                    username=user.username,
                    name=user.name,
                    verified=user.verified,
                    role=user.role,
                    last_login=user.last_login,
                    created_at=user.created_at,
                    updated_at=user.updated_at,
                )
            )

        return UsersOut(list=filtered, count=len(users))
    except Exception as e:
        raise HTTPException(400, str(e))


@router.get("/users/{user_id}")
async def get_user(
    user_id: int,
    header: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    db: Session = Depends(get_db),
) -> UserOut:
    try:
        user = db.query(Users).filter(Users.id == user_id).first()

        return UserOut(
            id=user.id,
            username=user.username,
            name=user.name,
            verified=user.verified,
            role=user.role,
            last_login=user.last_login,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    except Exception as e:
        raise HTTPException(400, str(e))


@router.patch("/online")
async def active(
    header: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    redis: Redis = Depends(get_redis),
):
    try:
        access_token = get_bearer_token(header)

        payload = decode(access_token)

        id = payload["id"]

        await redis.setex(f"online:{id}", 60 * 5, dumps(True))

        return {"message": "User activated successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/online")
async def active(user_id: int = Path(...), redis: Redis = Depends(get_redis)):
    try:
        online_json = await redis.get(f"online:{user_id}")
        return online_json
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))
