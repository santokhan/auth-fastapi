from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials


def get_bearer_token(authorization: HTTPAuthorizationCredentials) -> str:
    """
    Extracts and returns the bearer token from the Authorization header.

    Note:
    - This function handles errors internally and raises appropriate exceptions
      if the Authorization header is invalid or missing.
    - Do not wrap this function in a try/except block, as it is designed to
      handle its own error responses.
    """
    if authorization.scheme != "Bearer":
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    else:
      return authorization.credentials
