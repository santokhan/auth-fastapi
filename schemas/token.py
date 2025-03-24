from pydantic import BaseModel


class TokenResponse(BaseModel):
    refresh_token: str