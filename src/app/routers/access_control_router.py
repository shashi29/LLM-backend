from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any
from app.repositories.access_control_repository import AccessControlRepository

router = APIRouter(prefix="/access-control", tags=["AccessControl"])

# Instance of Access Control Repository
access_control_repository = AccessControlRepository()


@router.post("/grant", status_code=status.HTTP_201_CREATED)
async def grant_access(
    user_id: int, resource_id: int, resource_type: str, permissions: Dict[str, Any]
):
    """
    Grant specific permissions to a user for a resource.
    """
    try:
        access_control_repository.grant_permissions(user_id, resource_id, resource_type, permissions)
        return {"status_code": 201, "detail": "Permissions granted successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to grant permissions: {str(e)}",
        )


@router.post("/revoke", status_code=status.HTTP_200_OK)
async def revoke_access(user_id: int, resource_id: int, resource_type: str):
    """
    Revoke specific permissions from a user for a resource.
    """
    try:
        access_control_repository.revoke_permissions(user_id, resource_id, resource_type)
        return {"status_code": 200, "detail": "Permissions revoked successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke permissions: {str(e)}",
        )


@router.get("/permissions/{user_id}", response_model=List[Dict[str, Any]])
async def get_user_permissions(user_id: int, resource_type: str):
    """
    Retrieve all permissions for a user for a specific resource type.
    """
    try:
        permissions = access_control_repository.get_user_permissions(user_id, resource_type)
        if not permissions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="No permissions found"
            )
        return permissions
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve permissions: {str(e)}",
        )


@router.post("/check", response_model=bool)
async def check_access(
    user_id: int, resource_id: int, resource_type: str, action: str
):
    """
    Check if a user has a specific permission for a resource.
    """
    try:
        has_permission = access_control_repository.check_permission(
            user_id, resource_id, resource_type, action
        )
        return has_permission
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check permissions: {str(e)}",
        )
