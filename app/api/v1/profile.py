from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from shutil import copyfileobj
from os import makedirs, path
import uuid
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from db import get_db
from models import Users
from fastapi import Depends
from app.api.v1.users.helper.token import decode
from sqlalchemy.orm import Session

router = APIRouter()


def generate_filename(filename: str):
    return f"{uuid.uuid4().hex}{path.splitext(filename)[1]}"


@router.post("/upload", tags=["profile"])
async def upload_profile_image(
    image: UploadFile = File(...),
    header: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    db: Session = Depends(get_db),
):
    try:
        payload = decode(header.credentials)

        # Generate a new filename and set the path
        filename = generate_filename(image.filename)
        file_path = f"uploads/{filename}"

        # Ensure the 'uploads' directory exists
        if not path.exists("uploads"):
            makedirs("uploads")

        # Save the file to disk
        with open(file_path, "wb") as f:
            copyfileobj(image.file, f)

        # Update the user's image path in the database
        db.query(Users).filter(Users.id == payload["id"]).update({"image": filename})
        db.commit()

        return {"filename": filename}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
