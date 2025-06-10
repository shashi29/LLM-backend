# app/routers/main_board_router.py
from fastapi import APIRouter, Depends, HTTPException, status, Header
from typing import List, Optional
from app.models.main_board import MainBoard
from app.repositories.main_board_repository import MainBoardRepository
from app.repositories.client_user_repository import ClientUsersRepository
from jose import JWTError, jwt
from datetime import datetime
from sqlalchemy import text


router = APIRouter(prefix="/main-boards", tags=["Main Boards"])

# Creating instances of repositories
main_board_repository = MainBoardRepository()
users_repository = ClientUsersRepository()

# Authentication dependency
async def get_current_user_id(authorization: Optional[str] = Header(None)):
    # if not authorization:
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="Not authenticated",
    #         headers={"WWW-Authenticate": "Bearer"},
    #     )
    
    try:
        print("Authorization Header:", authorization)
        scheme, token = authorization.split()
        # if scheme.lower() != "bearer":
        #     raise HTTPException(
        #         status_code=status.HTTP_401_UNAUTHORIZED,
        #         detail="Invalid authentication scheme",
        #         headers={"WWW-Authenticate": "Bearer"},
        #     )
        
        payload = jwt.decode(token, "test_token", algorithms=["HS256"])
        email = payload.get("sub")
        # if email is None:
        #     raise HTTPException(
        #         status_code=status.HTTP_401_UNAUTHORIZED,
        #         detail="Invalid token",
        #         headers={"WWW-Authenticate": "Bearer"},
        #     )
        
        # Get user by email
        query = text("""
            SELECT id FROM ClientUsers WHERE email = :email;
        """)
        values = {"email": email}
        user_id = users_repository.execute_query(query, values)
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return user_id[0]
        
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Check if trial is active
async def check_trial_active(user_id: int):
    if not users_repository.is_trial_active(user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Trial period has expired. Please upgrade your subscription."
        )
    return user_id

@router.post("/", response_model=MainBoard)
async def create_main_board(main_board: MainBoard, user_id: int = Depends(check_trial_active)):
    try:
        # Set the client_user_id to the authenticated user's ID
        main_board.client_user_id = user_id
        created_main_board = main_board_repository.create_main_board(main_board)
        return created_main_board
    except ValueError as e:
        # Handle the specific duplicate name error
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while creating the main board: {str(e)}"
        )

@router.get("/", response_model=List[MainBoard])
async def get_all_main_boards(user_id: int = Depends(check_trial_active)):
    # Get only main boards owned by this user
    main_boards = main_board_repository.get_main_boards_by_user(user_id)
    order = ["ANALYSIS", "FORECASTING", "REVENUE", "PROFITABILITY", "COGS", "CASH FLOW", "BUDGET", "VARIANCE ANALYSIS", "RAG"]
    main_boards = sorted(main_boards, key=lambda x: order.index(x.name) if x.name in order else len(order))
    
    return main_boards

@router.get("/get_all_info_tree", response_model=list)
async def get_all_info_tree(user_id: int = Depends(check_trial_active)):
    try:
        # Get only the info tree for this user
        all_info_tree = main_board_repository.get_user_info_tree(user_id)

        if not all_info_tree:
            return []  # Return empty list if no main boards found

        return all_info_tree
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@router.get("/{main_board_id}", response_model=MainBoard)
async def get_main_board(main_board_id: int, user_id: int = Depends(check_trial_active)):
    try:
        # Check if the main board is owned by this user
        if not main_board_repository.is_main_board_owned_by_user(main_board_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. This main board does not belong to you."
            )
            
        main_board = main_board_repository.get_main_board(main_board_id)
        if not main_board:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Main Board not found")
        return main_board
    except HTTPException as e:
        raise e

@router.put("/{main_board_id}", response_model=MainBoard)
async def update_main_board(main_board_id: int, main_board: MainBoard, user_id: int = Depends(check_trial_active)):
    try:
        # Check if the main board is owned by this user
        if not main_board_repository.is_main_board_owned_by_user(main_board_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. This main board does not belong to you."
            )
            
        # Preserve the original user ID - don't let users change ownership
        main_board.client_user_id = user_id
        updated_main_board = main_board_repository.update_main_board(main_board_id, main_board)
        if not updated_main_board:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Main Board not found")
        return updated_main_board
    except ValueError as e:
        # Handle the specific duplicate name error
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while updating the main board: {str(e)}"
        )

@router.delete("/{main_board_id}", response_model=MainBoard)
async def delete_main_board(main_board_id: int, user_id: int = Depends(check_trial_active)):
    try:
        # Check if the main board is owned by this user
        if not main_board_repository.is_main_board_owned_by_user(main_board_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. This main board does not belong to you."
            )
            
        deleted_main_board = main_board_repository.delete_main_board(main_board_id)
        if not deleted_main_board:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Main Board not found")
        return deleted_main_board
    except HTTPException as e:
        raise e