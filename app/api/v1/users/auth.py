from fastapi import HTTPException, APIRouter, Header
from fastapi.responses import RedirectResponse
from app.config import db
from .helper.bearer import get_bearer_token
from .helper.hash import verify_hash, make_hash
from .helper.schemas import AccessTokenResponse, TokenResponse
from .helper.models import ForgotModel, ResetModel, UserModel, TokenInputModel
from .helper.token import (
    create_access_token,
    create_refresh_token,
    decode,
    refresh_access_token,
)

router = APIRouter()

users_collection = db["users"]


@router.post("/register")
async def register(user: UserModel) -> dict:
    try:
        user.validate_phone_number()

        user.validate_password()

        existing_user = await users_collection.find_one(
            {"$or": [{"email": user.email}, {"phone": user.phone}]}
        )
        if existing_user:
            raise HTTPException(status_code=400, detail="User already exists")

        users_collection.insert_one(
            {
                "email": user.email,
                "phone": user.phone,
                "password": make_hash(user.password),
                "verified": False,
            }
        )

        return {"message": "User registered successfully"}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login")
async def login(user: UserModel) -> TokenResponse:
    if not user.email and not user.phone:
        raise HTTPException(status_code=400, detail="Email or phone must be provided")
    try:
        filter = {"$or": [{"email": user.email}, {"phone": user.phone}]}
        db_user = await users_collection.find_one(filter)

        verify_hash(hash=db_user["password"], user_password=user.password)

        # Set to token
        user_data = {}
        for key in ["email", "phone"]:
            if user_data.get(key):
                db_user[key] = user_data.get(key)

        # Store to databaes that help on logout
        refresh_token = create_refresh_token(user_data)
        await users_collection.update_one(
            filter, {"$set": {"refresh_token": refresh_token}}
        )

        access_token = create_access_token(user_data)

        return TokenResponse(
            access_token=access_token, refresh_token=refresh_token, token_type="bearer"
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/token")
async def token(token: TokenInputModel) -> AccessTokenResponse:
    doc = await users_collection.find_one({"refresh_token": token.refresh_token})
    if doc is None:
        raise HTTPException(status_code=400, detail="Invalid token")

    return {"access_token": refresh_access_token(token.refresh_token)}


@router.post("/logout")
async def logout(authorization: str = Header(None)) -> dict:
    print(authorization)
    bearer_token = get_bearer_token(authorization)
    user_data = decode(bearer_token)

    filter = {}
    for key in ["email", "phone"]:
        if user_data.get(key):
            filter[key] = user_data.get(key)

    await users_collection.update_one(filter, {"$unset": {"refresh_token": ""}})

    return {"message": "User logged out successfully"}


@router.post("/forgot")
async def register(user: ForgotModel):
    try:
        user.validate_phone_number()

        db_user = await users_collection.find_one(
            {"$or": [{"email": user.email}, {"phone": user.phone}]}
        )

        # Set to token
        user_data = {}
        for key in ["email", "phone"]:
            if user_data.get(key):
                db_user[key] = user_data.get(key)

        reset_token = create_access_token(user_data)

        if user.callback:
            return RedirectResponse(url=f"{user.callback}?token={reset_token}")
        else:
            return RedirectResponse(url=f"/reset?token={reset_token}")

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/reset")
async def reset_form():
    return {"message": "Welcome to reset form"}


@router.post("/reset")
async def reset(reset: ResetModel):
    try:
        filter = {"$or": [{"email": reset.email}, {"phone": reset.phone}]}

        updated = await users_collection.update_one(
            filter, {"$set": {"password": make_hash(reset.password)}}
        )

        if updated is None:
            raise HTTPException(status_code=400, detail="Reset failed.")

        return {"message": "Password reset successful."}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))