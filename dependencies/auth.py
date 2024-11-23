from fastapi import Depends, HTTPException

# Dependency to check role access
def check_role_access(user_role: int, required_role: int):
    if user_role != required_role:
        raise HTTPException(status_code=403, detail="Access forbidden")
    return True
