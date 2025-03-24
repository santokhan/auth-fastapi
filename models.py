from sqlalchemy import Column, Integer, String, DateTime, Boolean, func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Users(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(50))
    email = Column(String(50), unique=True, nullable=False)
    phone = Column(String(50), unique=True)
    username = Column(String(50), unique=True)
    password = Column(String(255), nullable=False)
    role = Column(String(50), default="user")
    image = Column(String(255), nullable=True)
    verified = Column(Boolean, default=False)
    status = Column(String(50))

    last_login = Column(DateTime)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
