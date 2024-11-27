from pydantic import BaseModel

class RoleAssignment(BaseModel):
    role_id: int
    board_id: int
