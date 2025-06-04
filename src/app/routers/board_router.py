# app/routers/boards_router.py
from fastapi import APIRouter, Depends, HTTPException, Header
from typing import List, Optional
from app.repositories.boards_repository import BoardsRepository
from app.repositories.main_board_repository import MainBoardRepository
from app.models.boards import Boards
from app.routers.main_board_router import check_trial_active, get_current_user_id
from jose import JWTError, jwt
from fastapi import status

router = APIRouter(prefix="/boards", tags=["Boards"])

boards_repository = BoardsRepository()
main_board_repository = MainBoardRepository()

@router.post("/", response_model=Boards)
async def create_board(board: Boards, user_id: int = Depends(check_trial_active)):
    # Check if the main board belongs to this user
    if not main_board_repository.is_main_board_owned_by_user(board.main_board_id, user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. The main board does not belong to you."
        )
    
    created_board = boards_repository.create_board(board)
    return created_board

@router.get("/", response_model=List[Boards])
async def get_boards(user_id: int = Depends(check_trial_active)):
    # We won't implement filtering here as this endpoint should be used with caution
    # Instead, prefer using get_boards_for_main_boards with a main board ID that belongs to the user
    boards = boards_repository.get_boards()
    return boards

@router.get("/{board_id}", response_model=Boards)
async def get_board(board_id: int, user_id: int = Depends(check_trial_active)):
    # Check if the board belongs to this user
    if not boards_repository.is_board_owned_by_user(board_id, user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. This board does not belong to you."
        )
    
    board = boards_repository.get_board(board_id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    return board

@router.put("/{board_id}", response_model=Boards)
async def update_board(board_id: int, board: Boards, user_id: int = Depends(check_trial_active)):
    # Check if the board belongs to this user
    if not boards_repository.is_board_owned_by_user(board_id, user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. This board does not belong to you."
        )
    
    # Also check if the main board in the update belongs to this user
    if not main_board_repository.is_main_board_owned_by_user(board.main_board_id, user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. The target main board does not belong to you."
        )
    
    updated_board = boards_repository.update_board(board_id, board)
    if not updated_board:
        raise HTTPException(status_code=404, detail="Board not found")
    return updated_board

@router.delete("/{board_id}", response_model=dict)
async def delete_board(board_id: int, user_id: int = Depends(check_trial_active)):
    # Check if the board belongs to this user
    if not boards_repository.is_board_owned_by_user(board_id, user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. This board does not belong to you."
        )
    
    deleted_board = boards_repository.delete_board(board_id)
    if not deleted_board:
        raise HTTPException(status_code=404, detail="Board not found")
    response_data = {"status_code": 200, "detail": "Board deleted successfully"}
    return response_data

@router.get("/{main_board_id}/boards", response_model=List[Boards])
async def get_boards_for_main_boards(main_board_id: int, user_id: int = Depends(check_trial_active)):
    # Check if the main board belongs to this user
    if not main_board_repository.is_main_board_owned_by_user(main_board_id, user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. This main board does not belong to you."
        )
    
    boards = boards_repository.get_boards_for_main_boards(main_board_id)
    return boards