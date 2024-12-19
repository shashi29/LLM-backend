from typing import List, Optional, Dict, Any
from sqlalchemy import text
from app.repositories.base_repository import BaseRepository
import json

class AccessControlRepository(BaseRepository):
    def __init__(self):
        super().__init__('AccessControl')
        create_table_query = text("""
            CREATE TABLE IF NOT EXISTS AccessControl (
                id SERIAL PRIMARY KEY,
                user_id INT REFERENCES ClientUsers(id),
                resource_id INT NOT NULL,
                resource_type VARCHAR NOT NULL,
                permissions JSONB NOT NULL,
                UNIQUE (user_id, resource_id, resource_type)  -- Unique constraint for ON CONFLICT
            );
        """)
        self.create_table(create_table_query)

    def check_permission(self, user_id: int, resource_id: int, resource_type: str, action: str) -> bool:
        query = text("""
            SELECT permissions
            FROM AccessControl
            WHERE user_id = :user_id AND resource_id = :resource_id AND resource_type = :resource_type;
        """)
        values = {"user_id": user_id, "resource_id": resource_id, "resource_type": resource_type}
        result = self.execute_query(query, values)
        if not result:
            return False
        print(result[0], type(result[0]))
        permissions = result[0] 
        return action in permissions

    def get_user_permissions(self, user_id: int, resource_type: str) -> List[Dict[str, Any]]:
        query = text("""
            SELECT resource_id, permissions
            FROM AccessControl
            WHERE user_id = :user_id AND resource_type = :resource_type;
        """)
        values = {"user_id": user_id, "resource_type": resource_type}
        return self.execute_query_all(query, values)

    def grant_permissions(self, user_id: int, resource_id: int, resource_type: str, permissions: Dict) -> None:
        # Ensure that the permissions dictionary is serialized to a JSON string
        permissions_json = json.dumps(permissions)
        
        query = text("""
            INSERT INTO AccessControl (user_id, resource_id, resource_type, permissions)
            VALUES (:user_id, :resource_id, :resource_type, :permissions)
        """)
        values = {
            "user_id": user_id,
            "resource_id": resource_id,
            "resource_type": resource_type,
            "permissions": permissions_json  # Serialize permissions to JSON string
        }
        self.execute_query_no_return(query, values)
        
        
    def revoke_permissions(self, user_id: int, resource_id: int, resource_type: str) -> None:
        query = text("""
            DELETE FROM AccessControl
            WHERE user_id = :user_id AND resource_id = :resource_id AND resource_type = :resource_type;
        """)
        values = {"user_id": user_id, "resource_id": resource_id, "resource_type": resource_type}
        self.execute_query(query, values)
