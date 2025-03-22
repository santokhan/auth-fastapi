from fastapi import APIRouter, Depends, HTTPException
from db import get_db
from sqlalchemy.orm import Session
from models import Users

router = APIRouter()


@router.get("/")
async def root(db: Session = Depends(get_db)) -> dict:
    try:
        print(db.query(Users).all())
        return {"message": "Welcome back Santo! to your Authentication API server."}
    except Exception as e:
        raise HTTPException(500, str(e))
