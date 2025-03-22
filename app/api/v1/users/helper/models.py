import re
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional


class UserBase(BaseModel):
    username: Optional[str] = None
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    role: Optional[str] = None

    last_login: Optional[datetime] = None


class UserCreate(BaseModel):
    username: Optional[str] = Field(default="admin")
    name: Optional[str] = Field(default="Admin")
    email: Optional[EmailStr] = Field(default="inbox.santo@gmail.com")
    phone: Optional[str] = Field(default="0162260365")
    password: str = Field(default="Admin1234")
    role: Optional[str] = Field(default="user")

    # def validate_phone_number(self):
    #     if self.phone:  # validate only if user inputed
    #         try:
    #             parsed_number = parse(self.phone, "DE")
    #             if is_valid_number(parsed_number):
    #                 return parsed_number
    #             else:
    #                 raise ValueError("Invalid phone number")
    #         except Exception:
    #             raise ValueError("Invalid phone number format")
    #     return None

    def trim(self):
        return self.phone.strip()[-9:]

    def validate_password(self):
        if self.password:
            errors = []

            length = 6
            if len(self.password) < length:
                errors.append(f"Password must be at least {length} characters long.")
            if not re.search(r"[a-zA-Z]", self.password):
                errors.append("Password must contain at least one letter.")
            if not re.search(r"[0-9]", self.password):
                errors.append("Password must contain at least one number.")

            if errors:
                raise ValueError(" ".join(errors))


class UserSignIn(BaseModel):
    username: Optional[str] = Field(default="admin")
    email: Optional[EmailStr] = Field(default="inbox.santo@gmail.com")
    phone: Optional[str] = Field(default="0162260365")
    password: str = Field(default="Admin1234")


class UserOut(UserBase):
    id: int
    verified: Optional[bool] = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UsersOut(BaseModel):
    list: List[UserOut] = Field(default_factory=list)
    count: int = Field(default_factory=int)


class ForgotModel(BaseModel):
    email: Optional[EmailStr] = Field(default=None)
    username: Optional[str] = Field(default=None)
    phone: Optional[str] = Field(default=None, min_length=9, max_length=9)
    callback: Optional[str] = Field(
        default=None, detail="Reset form URL that client will send in body."
    )

    # def validate_phone_number(self):
    #     if self.phone:  # validate only if user inputed
    #         try:
    #             parsed_number = parse(self.phone, "BD")
    #             if is_valid_number(parsed_number):
    #                 return parsed_number
    #             else:
    #                 raise ValueError("Invalid phone number")
    #         except Exception:
    #             raise ValueError("Invalid phone number format")
    #     return None


class ResetModel(BaseModel):
    password: str = Field(default=None)
    token: str = Field(default=None, description="Token including user object.")

    # def validate_phone_number(self):
    #     if self.phone:  # validate only if user inputed
    #         try:
    #             parsed_number = parse(self.phone, "BD")
    #             if is_valid_number(parsed_number):
    #                 return parsed_number
    #             else:
    #                 raise ValueError("Invalid phone number")
    #         except Exception:
    #             raise ValueError("Invalid phone number format")
    #     return None


class TokenInputModel(BaseModel):
    refresh_token: str


class VerificationModel(BaseModel):
    callback_url: str = Field(description="Callback URL sent from client or app.")
