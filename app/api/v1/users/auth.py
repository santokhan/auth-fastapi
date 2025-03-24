from fastapi import Depends, HTTPException, APIRouter, Path, Body, Header, Request

# from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.api.v1 import sms
from db import get_db
from app.services.mail.sender import send_email, send_email_verification
from .helper.hash import verify_hash, make_hash
from db import get_redis
from aioredis.client import Redis
from schemas.user import (
    ForgotModel,
    # ResetModel,
    UserCreate,
    UserOut,
    UserSignIn,
)
from .helper.token import create_access_token, create_refresh_token, decode
from sqlalchemy.orm import Session
from models import Users
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from datetime import datetime

router = APIRouter(tags=["authentication"])


@router.post("/signup")
async def register(user: UserCreate, db: Session = Depends(get_db)) -> UserOut:
    try:
        user.validate_password()
        user.validate_username()

        user = Users(
            username=user.username,
            email=user.email,
            phone=user.phone,
            password=make_hash(user.password),
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        return UserOut(
            id=user.id,
            username=user.username,
            email=user.email,
            phone=user.phone,
            name=user.name,
            verified=user.verified,
            role=user.role,
            last_login=user.last_login,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    except IntegrityError as e:
        db.rollback()  # Rollback transaction to maintain DB consistency
        raise HTTPException(400, "Username or email already exists.")

    except SQLAlchemyError as e:
        db.rollback()  # Ensure rollback on any other database-related error
        raise HTTPException(500, "Database error occurred.")

    except Exception as e:
        raise HTTPException(400, str(e))


@router.post("/signin")
async def login(
    input: UserSignIn, db: Session = Depends(get_db), redis: Redis = Depends(get_redis)
) -> str:
    try:
        query = db.query(Users)

        if input.email:
            query = query.where(Users.email == input.email)
        elif input.phone:
            query = query.where(Users.phone == input.phone)
        else:
            raise HTTPException(
                status_code=400, detail="Email, phone, or username is required"
            )

        user = query.first()

        if user is None:
            raise HTTPException(status_code=404, detail="User not found")

        verify_hash(hash=user.password, user_password=input.password)

        db.query(Users).where(Users.id == user.id).update(
            {"last_login": datetime.now()}
        )

        db.commit()
        db.refresh(user)

        refresh_token = create_refresh_token(data={"id": user.id})

        await redis.setex(f"refresh_token:{user.id}", 60 * 60 * 24 * 7, refresh_token)

        return refresh_token

    except SQLAlchemyError as e:
        db.rollback()  # Ensure rollback on any other database-related error
        raise HTTPException(500, "Database error occurred.")

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/token")
async def token(
    token: str = Body(...),
    redis: Redis = Depends(get_redis),
    db: Session = Depends(get_db),
) -> str:
    try:
        payload = decode(token)

        refresh_token = await redis.get(f"refresh_token:{payload['id']}")

        if refresh_token != token:
            raise HTTPException(status_code=400, detail="Invalid refresh token")

        user = db.query(Users).where(Users.id == payload.get("id")).first()

        access_token = create_access_token(
            data={
                "id": user.id,
                "username": user.username,
                "name": user.name,
                "phone": user.phone,
                "email": user.email,
                "verified": user.verified,
                "role": user.role,
                "last_login": str(user.last_login),
                "created_at": str(user.created_at),
                "updated_at": str(user.updated_at),
            }
        )

        return access_token

    except SQLAlchemyError as e:
        db.rollback()  # Ensure rollback on any other database-related error
        raise HTTPException(500, "Database error occurred.")

    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid request")


@router.post("/signout")
async def logout(
    header: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    redis: Redis = Depends(get_redis),
):
    try:
        payload = decode(header.credentials)

        key = f"refresh_token:{payload.get('id')}"

        await redis.delete(key)

        return {"message": "User logged out successfully"}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/forgot")
async def forgot(
    request: Request,
    referer: str = Header(default=None),
    input: ForgotModel = Body(...),
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    try:
        if not (input.email or input.username or input.phone):
            raise HTTPException(400, "Email, Username or Phone is required.")

        db_user = (
            db.query(Users)
            .filter(
                Users.email == input.email
                or Users.username == input.username
                or Users.phone == input.phone
            )
            .first()
        )

        if db_user is None:
            raise HTTPException(400, "User not found")

        reset_token = create_access_token({"id": db_user.id})

        # Store the reset token in Redis for 10 minutes
        await redis.setex(f"reset_token:{db_user.id}", 60 * 10, reset_token)

        full_url = f"{request.url.scheme}://{request.url.netloc}"
        params = {"token": reset_token, "redirect": referer}
        query_string = "&".join(f"{key}={value}" for key, value in params.items())

        if input.callback:
            url_with_token = f"{input.callback}?{query_string}"
        else:
            url_with_token = f"{full_url}/api/v1/users/reset?{query_string}"

        # Send reset link via SMS or Email
        if db_user.email:
            try:
                await send_email(reset_link=url_with_token, to_email=input.email)
            except Exception as e:
                raise HTTPException(
                    status_code=500, detail=f"Email service error: {str(e)}"
                )
        elif db_user.phone:
            try:
                await sms.sms_sender(
                    message=f"SSI Mart \nTo reset your password, click the link: {url_with_token}",
                    mobile_no=input.phone,
                )
            except Exception as e:
                raise HTTPException(
                    status_code=500, detail=f"SMS service error: {str(e)}"
                )

        return {"message": "Password reset link has been sent."}

    except HTTPException as e:
        raise e  # Re-raise the HTTPException as it is
    except Exception as e:
        print(e)
        raise HTTPException(status_code=400, detail=f"Unexpected error: {str(e)}")


# @router.get("/reset", response_class=HTMLResponse)
# async def reset_form(token: str = Query(...)):
#     with open("static/reset.html", "r", encoding="utf-8") as file:
#         html_content = file.read()
#         if html_content:
#             return html_content


# @router.post("/reset")
# async def reset(reset_model: ResetModel):
#     try:
#         if reset_model.token is None or reset_model.password is None:
#             raise HTTPException(
#                 status_code=400, detail="Token and Password are required."
#             )

#         decoded_user = decode(reset_model.token)

#         id = decoded_user.get("id", None)

#         filter = {}
#         if id is not None:
#             filter["_id"] = ObjectId(id)

#         password = make_hash(reset_model.password)

#         updated = await collection.update_one(filter, {"$set": {"password": password}})

#         if updated is None:
#             raise HTTPException(
#                 status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Reset failed."
#             )

#         return {"message": "Password reset successful."}

#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))


# @router.delete("/{id}")
# async def delete(id: str = Path(...), db: Session = Depends(get_db)):
#     try:
#         db.query(Users).filter(Users.id == id).delete()

#         db.commit()

#         return {"message": "User deleted successfully."}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
