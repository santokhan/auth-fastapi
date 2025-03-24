from fastapi import HTTPException


def role_guard(role: str, allowed_roles: list[str]) -> bool:
    """
    role_guard is a function that takes in a role and a list of allowed roles.
    If the role is not in the allowed roles, then it raises a 403 error.
    """
    if role not in allowed_roles:
        raise HTTPException(403, "You are not authorized to access this route")
    else:
        return True
