from datetime import datetime
from shutil import ExecError
from bson import ObjectId
from fastapi import (
    Body,
    Depends,
    HTTPException,
    APIRouter,
    Header,
    Query,
    Request,
    status,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.api.v1 import sms
from app.config import db
from app.services.mail.sender import send_email, send_email_verification
from .helper.bearer import get_bearer_token
from .helper.hash import verify_hash, make_hash
from .helper.schemas import AccessTokenResponse, TokenResponse
from .helper.models import (
    ForgotModel,
    ResetModel,
    UserModel,
    TokenInputModel,
    UserResponse,
    UsersResponse,
    VerificationModel,
)
from pymongo.errors import PyMongoError
from .helper.token import (
    create_access_token,
    create_refresh_token,
    decode,
    refresh_access_token,
)
from app.api.v1.users.helper.token import decode

router = APIRouter()

collection = db["users"]


@router.post("/signup")
async def register(user: UserModel) -> dict:
    try:
        user.validate_phone_number()
        user.validate_password()

        filter = {}
        if user.phone:
            filter["phone"] = user.phone
        if user.email:
            filter["email"] = user.email

        existing_user = await collection.find_one(filter)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="User already exists",
            )

        collection.insert_one(
            {
                "email": user.email,
                "phone": user.phone,
                "username": user.username,
                "name": user.name,
                "password": make_hash(user.password),
                "verified": False,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            }
        )

        return {"message": "User registered successfully"}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/signin")
async def login(user: UserModel) -> TokenResponse:
    if not user.email and not user.phone:
        raise HTTPException(status_code=400, detail="Email or phone must be provided")
    try:
        filter = {}
        if user.email:
            filter["email"] = user.email
        elif user.phone:
            filter["phone"] = user.phone

        db_user = await collection.find_one(filter)

        if db_user is None:
            raise HTTPException(status_code=404, detail="User not found")

        verify_hash(hash=db_user["password"], user_password=user.password)

        # Set to token
        user_data = {
            "id": str(db_user.get("_id", None)),
            "name": db_user.get("name", None),
            "email": db_user.get("email", None),
            "phone": db_user.get("phone", None),
            "username": db_user.get("username", None),
            "verified": db_user.get("verified", None),
        }

        # Store to databaes that help on logout
        refresh_token = create_refresh_token(user_data)
        await collection.update_one(filter, {"$set": {"refresh_token": refresh_token}})

        access_token = create_access_token(user_data)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=user_data,
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/token")
async def token(token: TokenInputModel) -> AccessTokenResponse:
    decode(token.refresh_token)

    try:
        user = await collection.find_one({"refresh_token": token.refresh_token})
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
            )

        user_data = {
            "id": str(user.get("_id", None)),
            "name": user.get("name", None),
            "email": user.get("email", None),
            "phone": user.get("phone", None),
            "username": user.get("username", None),
            "verified": user.get("verified", None),
        }

        return {"access_token": create_access_token(user_data)}

    except ExecError as e:
        raise HTTPException(status_code=400, detail="Invalid request")


@router.post("/signout")
async def logout(header: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    access_token = get_bearer_token(header.credentials)

    user_data = decode(access_token)

    filter = {}
    for key in ["email", "phone"]:
        if user_data.get(key):
            filter[key] = user_data.get(key)

    await collection.update_one(filter, {"$unset": {"refresh_token": ""}})

    return {"message": "User logged out successfully"}


@router.post("/forgot")
async def forgot(
    request: Request, referer: str = Header(default=None), user: ForgotModel = Body(...)
):
    try:
        user.validate_phone_number()

        filter = {}
        if user.email:
            filter["email"] = user.email
        elif user.phone:
            filter["phone"] = user.phone
        elif user.username:
            filter["username"] = user.username

        db_user = await collection.find_one(filter)

        if db_user is None:
            raise HTTPException(
                status_code=204, detail="Not user found with the given email"
            )

        id = str(db_user.get("_id", None))

        if id is None:
            raise HTTPException(
                status_code=200, detail="To create token user id is required."
            )

        reset_token = create_access_token({"id": id})

        full_url = f"{request.url.scheme}://{request.url.netloc}"
        params = {"token": reset_token, "redirect": referer}
        query_string = "&".join(f"{key}={value}" for key, value in params.items())

        url_with_token = ""
        if user.callback is not None:
            url_with_token = f"{user.callback}?{query_string}"
        else:
            url_with_token = f"{full_url}/api/v1/users/reset?{query_string}"

        # Send reset link via SMS or Email
        if filter.get("phone"):
            await sms.sms_sender(
                message=f"SSI Mart \nTo reset your password, click the link: {url_with_token}",
                mobile_no=filter.get("phone"),
            )
        elif filter.get("email"):
            await send_email(reset_link=url_with_token, to_email=filter.get("email"))

        return {"message": "Password reset link has been sent.", "to": user}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/reset", response_class=HTMLResponse)
async def reset_form(token: str = Query(...)):
    with open("static/reset.html", "r", encoding="utf-8") as file:
        html_content = file.read()
        if html_content:
            return html_content


@router.post("/reset")
async def reset(reset_model: ResetModel):
    try:
        if reset_model.token is None or reset_model.password is None:
            raise HTTPException(
                status_code=400, detail="Token and Password are required."
            )

        decoded_user = decode(reset_model.token)

        id = decoded_user.get("id", None)

        filter = {}
        if id is not None:
            filter["_id"] = ObjectId(id)

        password = make_hash(reset_model.password)

        updated = await collection.update_one(filter, {"$set": {"password": password}})

        if updated is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Reset failed."
            )

        return {"message": "Password reset successful."}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/verify")
async def get_verification_email(
    request: Request,
    header: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    verification_model: VerificationModel = Body(),
):
    callback_url = verification_model.callback_url
    user = decode(header.credentials)

    try:
        user_id = user.get("id")
        if not user_id:
            raise HTTPException(status_code=400, detail="User ID not found in token.")

        db_user = await collection.find_one({"_id": ObjectId(user_id)})
        if not db_user:
            raise HTTPException(status_code=404, detail="No user found.")

        verification_token = create_access_token({"id": user_id})

        query_string = f"token={verification_token}&redirect={callback_url}"

        url_with_token = f"{request.url._url}?{query_string}"

        await send_email_verification(
            verification_link=url_with_token, to_email=db_user["email"]
        )

        return {"message": "Password reset link has been sent."}

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")


@router.get("/verify")
async def verify(token: str = Query(...), redirect: str = Query(...)):
    try:
        user = decode(token)

        user_id = user.get("id")
        if not user_id:
            raise HTTPException(status_code=400, detail="User ID not found in token.")

        filter = {"_id": ObjectId(user_id)}

        updated = await collection.update_one(filter, {"$set": {"verified": True}})
        if updated.modified_count == 0:
            raise HTTPException(
                status_code=404, detail="User not found or already verified."
            )

        return RedirectResponse(url=redirect)

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{id}", response_model=UserResponse)
async def user(id: str):
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid 'id' provided")

    try:
        doc = await collection.find_one({"_id": ObjectId(id)})

        if doc is None:
            raise HTTPException(status_code=404, detail=f"Item with id {id} not found")

        return UserResponse(
            id=str(doc.get("_id")),
            email=doc.get("email"),
            phone=doc.get("phone"),
            verified=doc.get("verified"),
            created_at=doc.get("created_at"),
            updated_at=doc.get("updated_at"),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


VALID_SORT_FIELDS = ["created_at", "updated_at", "email", "name", "phone"]


@router.get("", response_model=UsersResponse)
async def users(
    sort_by: str = "created_at", sort_order: int = -1, skip: int = 0, limit: int = 10
):
    try:
        # Validate the sort_by field
        if sort_by not in VALID_SORT_FIELDS:
            raise ValueError(f"Invalid sort field: {sort_by}")

        # Validate the sort_order field
        if sort_order not in [1, -1]:
            raise ValueError("sort_order must be 1 (ascending) or -1 (descending)")

        filters = {}

        # Query the database with sorting, skipping, and limiting
        users = (
            await collection.find(filters)
            .sort(sort_by, sort_order)
            .skip(skip)
            .limit(limit)
            .to_list(length=None)
        )
        count = await collection.count_documents(filters)

        # If no users are found, return an empty list
        if not users:
            return {"users": []}

        # Using list comprehension to build the filtered response
        filtered = []

        for user in users:
            _id = user.get("_id", None)
            if _id is not None:
                filtered.append(
                    UserResponse(
                        id=str(_id),
                        email=user.get("email", None),
                        phone=user.get("phone", None),
                        verified=user.get("verified", False),
                        created_at=user.get("created_at"),
                        updated_at=user.get("updated_at"),
                    )
                )

        return {"list": filtered, "count": count}

    except PyMongoError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid input: {str(e)}",
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}",
        )


@router.delete("/{id}")
async def delete(id: str):
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid 'id' provided")

    try:
        result = await collection.delete_one({"_id": ObjectId(id)})

        # If no document was deleted, the id might not exist in the database
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail=f"Item with id {id} not found")

        return {"message": "User has been deleted.", "id": id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
