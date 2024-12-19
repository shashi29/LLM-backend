# app/routers/main_board_router.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.models.main_board import MainBoard
from app.repositories.main_board_repository import MainBoardRepository
from app.repositories.access_control_repository import AccessControlRepository

router = APIRouter(prefix="/main-boards", tags=["Main Boards"])

# Creating an instance of the MainBoardRepository
main_board_repository = MainBoardRepository()

@router.post("/", response_model=MainBoard)
async def create_main_board(main_board: MainBoard):
    try:
        created_main_board = main_board_repository.create_main_board(main_board.client_user_id, main_board)
        return created_main_board
    except HTTPException as e:
        raise e

@router.get("/", response_model=List[MainBoard])
async def get_all_main_boards(user_id: int):
    main_boards = main_board_repository.get_all_main_boards(user_id)
    #order = ["Analysis", "FORECASTING", "REVENUE", "PROFITABILITY", "COGS", "CASH FLOW", "BUDGET", "VARIANCE ANALYSIS"]
    #main_boards = sorted(main_boards, key=lambda x: order.index(x.name))
    
    return main_boards

@router.get("/get_all_info_tree", response_model=list)
async def get_all_info_tree(user_id: int):
    # try:
    all_info_tree = main_board_repository.get_all_info_tree(user_id)

    if not all_info_tree:
        raise HTTPException(status_code=404, detail="Main Board not found")

    return all_info_tree
    # except Exception as e:
    #     raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@router.get("/{main_board_id}", response_model=MainBoard)
async def get_main_board(user_id: int, main_board_id: int):
    try:
        main_board = main_board_repository.get_main_board(user_id, main_board_id)
        if not main_board:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Main Board not found")
        return main_board
    except HTTPException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e)

@router.put("/{main_board_id}", response_model=MainBoard)
async def update_main_board(user_id: int, main_board_id: int, main_board: MainBoard):
    try:
        updated_main_board = main_board_repository.update_main_board(user_id, main_board)
        if not updated_main_board:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Main Board not found")
        return updated_main_board
    except HTTPException as e:
        raise e

@router.delete("/{main_board_id}", response_model=MainBoard)
async def delete_main_board(user_id: int, main_board_id: int):
    try:
        deleted_main_board = main_board_repository.delete_main_board(user_id, main_board_id)
        if not deleted_main_board:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Main Board not found")
        return deleted_main_board
    except HTTPException as e:
        raise e