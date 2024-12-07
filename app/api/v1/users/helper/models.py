from datetime import datetime
import re
from phonenumbers import is_valid_number, parse
from pydantic import BaseModel, EmailStr, Field, model_validator
from typing import List, Optional


class UserModel(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(
        default=None, min_length=11, max_length=11
    )  # Store as a string for initial input
    password: str

    def validate_phone_number(self):
        if self.phone:  # validate only if user inputed
            try:
                parsed_number = parse(self.phone, "BD")
                if is_valid_number(parsed_number):
                    return parsed_number
                else:
                    raise ValueError("Invalid phone number")
            except Exception:
                raise ValueError("Invalid phone number format")
        return None

    def trim(self):
        return self.phone.strip()[-11:]

    def validate_password(self):
        if self.password:  # validate only if user inputed
            errors = []

            if len(self.password) < 6:
                errors.append("must be at least 6 characters long.")
            if not re.search(r"[a-zA-Z]", self.password):
                errors.append("must contain at least one letter.")
            if not re.search(r"[0-9]", self.password):
                errors.append("must contain at least one number.")

            if errors:
                raise ValueError("Invalid password: " + " ".join(errors))

        return "Valid password"


class UserResponse(BaseModel):
    id: str
    email: Optional[str] = None
    phone: Optional[str] = None
    verified: Optional[bool] = False
    created_at: datetime
    updated_at: datetime

    # Model validator to check that at least one of email or phone is provided
    @model_validator(mode="before")
    def check_email_or_phone(cls, values):
        email = values.get("email")
        phone = values.get("phone")

        if not email and not phone:
            raise ValueError('At least one of "email" or "phone" must be provided.')

        return values


class UsersResponse(BaseModel):
    list: List[UserResponse] = Field(default_factory=list)
    count: int = Field(default_factory=int)


class ForgotModel(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = Field(
        default=None, min_length=11, max_length=11
    )  # Store as a string for initial input
    callback: Optional[str] = None

    def validate_phone_number(self):
        if self.phone:  # validate only if user inputed
            try:
                parsed_number = parse(self.phone, "BD")
                if is_valid_number(parsed_number):
                    return parsed_number
                else:
                    raise ValueError("Invalid phone number")
            except Exception:
                raise ValueError("Invalid phone number format")
        return None


class ResetModel(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(
        default=None, min_length=11, max_length=11
    )  # Store as a string for initial input
    password: str
    token: str

    def validate_phone_number(self):
        if self.phone:  # validate only if user inputed
            try:
                parsed_number = parse(self.phone, "BD")
                if is_valid_number(parsed_number):
                    return parsed_number
                else:
                    raise ValueError("Invalid phone number")
            except Exception:
                raise ValueError("Invalid phone number format")
        return None


class TokenInputModel(BaseModel):
    refresh_token: str
