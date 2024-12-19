from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.repositories.boards_repository import BoardsRepository
from app.models.boards import Boards

router = APIRouter(prefix="/boards", tags=["Boards"])

# Instance of Boards Repository
boards_repository = BoardsRepository()

@router.post("/", response_model=Boards)
async def create_board(user_id: int, board: Boards):
    """
    Create a new board for the specified user.
    """
    created_board = boards_repository.create_board(user_id, board)
    if not created_board:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to create board")
    return created_board

@router.get("/", response_model=List[Boards])
async def get_boards(user_id: int):
    """
    Get all boards for the specified user.
    """
    boards = boards_repository.get_boards(user_id)
    if not boards:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No boards found")
    return boards

@router.get("/{board_id}", response_model=Boards)
async def get_board(user_id: int, board_id: int):
    """
    Get a specific board for the specified user.
    """
    board = boards_repository.get_board(user_id, board_id)
    if not board:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Board not found")
    return board

@router.put("/{board_id}", response_model=Boards)
async def update_board(user_id: int, board_id: int, board: Boards):
    """
    Update a specific board for the specified user.
    """
    updated_board = boards_repository.update_board(user_id, board_id, board)
    if not updated_board:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Board not found or update failed")
    return updated_board

@router.delete("/{board_id}", response_model=dict)
async def delete_board(user_id: int, board_id: int):
    """
    Delete a specific board for the specified user.
    """
    deleted_board = boards_repository.delete_board(user_id, board_id)
    if not deleted_board:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Board not found or delete failed")
    return {"status_code": 200, "detail": "Board deleted successfully"}

@router.get("/{main_board_id}/boards", response_model=List[Boards])
async def get_boards_for_main_board(user_id: int, main_board_id: int):
    """
    Get all boards for a specific main board and user.
    """
    boards = boards_repository.get_boards_for_main_board(user_id, main_board_id)
    if not boards:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No boards found for this Main Board")
    return boards
