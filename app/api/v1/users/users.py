from fastapi import Depends, HTTPException, APIRouter, Path
from db import get_db, get_redis
from lib.role_guard import role_guard
from schemas.user import UserOut, UsersOut
from sqlalchemy.orm import Session
from models import Users
from aioredis.client import Redis
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from json import dumps
from .helper.token import decode
from sqlalchemy.exc import SQLAlchemyError

router = APIRouter()


@router.patch(
    "/make_admin/{user_id}",
    tags=["admin"],
    description="Only super-admin can access this route",
)
async def make_admin(
    user_id: int,
    header: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    db: Session = Depends(get_db),
):
    try:
        payload = decode(header.credentials)
        role_guard(payload.get("role"), ["super-admin", "admin"])

        db.query(Users).where(Users.id == user_id).update({"role": "admin"})
        db.commit()

        return {"message": "User role updated successfully."}

    except SQLAlchemyError as e:
        db.rollback()  # Ensure rollback on any other database-related error
        raise HTTPException(500, "Database error occurred.")

    except Exception as e:
        raise HTTPException(400, str(e))


@router.get("/users", tags=["admin"], description="Only admin can access this route")
async def get_users(
    header: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    db: Session = Depends(get_db),
) -> UsersOut:
    # check if user is admin
    payload = decode(header.credentials)
    role_guard(payload.get("role"), ["admin"])

    try:
        users = db.query(Users).all()

        filtered = []

        for user in users:
            filtered.append(
                UserOut(
                    id=user.id,
                    username=user.username,
                    email=user.email,
                    phone=user.phone,
                    name=user.name,
                    image=user.image,
                    verified=user.verified,
                    role=user.role,
                    status=user.status,
                    last_login=user.last_login,
                    created_at=user.created_at,
                    updated_at=user.updated_at,
                )
            )

        return UsersOut(list=filtered, count=len(users))
    
    except Exception as e:
        raise HTTPException(400, str(e))


@router.get(
    "/users/{user_id}",
    tags=["admin"],
    description="Only super-admin can access this route",
)
async def get_user(
    user_id: int,
    header: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    db: Session = Depends(get_db),
) -> UserOut:
    # check if user is admin
    payload = decode(header.credentials)
    role_guard(payload.get("role"), ["admin"])

    try:
        user = db.query(Users).filter(Users.id == user_id).first()

        return UserOut(
            id=user.id,
            username=user.username,
            name=user.name,
            image=user.image,
            verified=user.verified,
            role=user.role,
            status=user.status,
            last_login=user.last_login,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    except Exception as e:
        raise HTTPException(400, str(e))


@router.patch("/users/{id}/disable", tags=["admin"])
async def delete(id: str = Path(...), db: Session = Depends(get_db)):
    try:
        user = db.query(Users).where(Users.id == id).first()

        user.status = "disaled"

        db.commit()

        return {"message": "User deleted successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/online", tags=["user"])
async def active(
    header: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    redis: Redis = Depends(get_redis),
):
    try:
        payload = decode(header.credentials)

        id = payload.get("id")

        await redis.setex(f"online:{id}", 60 * 5, dumps(True))

        return {"message": "User activated successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/online", tags=["user"])
async def active(user_id: int = Path(...), redis: Redis = Depends(get_redis)):
    try:
        online = await redis.exists(f"online:{user_id}")
        return True if online else False
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))
