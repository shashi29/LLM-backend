from pydantic import BaseModel

class UserRole(BaseModel):
    user_id: int
    role_id: int
