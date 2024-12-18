from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.repositories.quadrant_collection_repository import QuadrantCollectionTableRepository
from app.models.quadrant_collection import QuadrantCollectionTable

router = APIRouter(prefix="/quadrant-collection", tags=["Quadrant Collection Table"])

quadrant_collection_table_repository = QuadrantCollectionTableRepository()

@router.post("/", response_model=QuadrantCollectionTable)
async def create_quadrant_collection_table(quadrant_collection_table: QuadrantCollectionTable):
    try:
        # Attempt to create Quadrant Collection Table
        created_table = quadrant_collection_table_repository.create_quadrant_collection_table(quadrant_collection_table)
        return created_table
    except Exception as e:
        # Check if the error is due to a duplicate key violation
        if "duplicate key value violates unique constraint" in str(e):
            raise HTTPException(status_code=400, detail="Quadrant Collection Table under this Board already exists")
        else:
            # Re-raise the exception if it's not related to duplicate key violation
            raise HTTPException(status_code=500, detail="Quadrant Collection Table API failed to process")

@router.get("/", response_model=List[QuadrantCollectionTable])
async def get_all_quadrant_collection_table():
    all_tables = quadrant_collection_table_repository.get_all_quadrant_collection_table()
    return all_tables

@router.get("/{doc_id}", response_model=QuadrantCollectionTable)
async def get_quadrant_collection_table(doc_id: int):
    table = quadrant_collection_table_repository.get_quadrant_collection_table(doc_id)
    if not table:
        raise HTTPException(status_code=404, detail="Quadrant Collection Table not found")
    return table

@router.put("/{doc_id}", response_model=QuadrantCollectionTable)
async def update_quadrant_collection_table(doc_id: int, quadrant_collection_table: QuadrantCollectionTable):
    updated_table = quadrant_collection_table_repository.update_quadrant_collection_table(doc_id, quadrant_collection_table)
    if not updated_table:
        raise HTTPException(status_code=404, detail="Quadrant Collection Table not found")
    return updated_table

@router.delete("/{doc_id}")
async def delete_quadrant_collection_table(doc_id: int):
    deleted_table = quadrant_collection_table_repository.delete_quadrant_collection_table(doc_id)
    if not deleted_table:
        raise HTTPException(status_code=404, detail="Quadrant Collection Table not found")
    return {"message": "Quadrant Collection Table deleted successfully"}
