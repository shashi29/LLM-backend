# app/routers/rag_router.py
import os
import tempfile
import json
from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from app.repositories.rag_repository import RAGRepository
from app.repositories.boards_repository import BoardsRepository
from app.models.rag_models import RAGCollection, ChatMessage, ChatSession, FileInfo, ChatStats
from app.routers.main_board_router import check_trial_active, get_current_user_id
from datetime import datetime

router = APIRouter(prefix="/rag", tags=["RAG System"])

rag_repository = RAGRepository()
boards_repository = BoardsRepository()

# Helper to check board ownership
async def verify_board_access(board_id: int, user_id: int = Depends(check_trial_active)):
    if not boards_repository.is_board_owned_by_user(board_id, user_id):
        raise HTTPException(
            status_code=403,
            detail="Access denied. This board does not belong to you."
        )
    return user_id

# Helper to check collection ownership
async def verify_collection_access(collection_id: int, user_id: int = Depends(check_trial_active)):
    collection = rag_repository.get_collection(collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
        
    if not boards_repository.is_board_owned_by_user(collection.board_id, user_id):
        raise HTTPException(
            status_code=403,
            detail="Access denied. This collection does not belong to you."
        )
    return collection

# Collection management
@router.post("/collections", response_model=RAGCollection)
async def create_collection(
    board_id: int = Form(...),
    collection_name: str = Form(...),
    vector_size: int = Form(384),
    distance: str = Form("COSINE"),
    user_id: int = Depends(check_trial_active)
):
    # Verify board ownership
    await verify_board_access(board_id, user_id)
    
    try:
        collection = RAGCollection(
            board_id=board_id,
            collection_name=collection_name,
            vector_size=vector_size,
            distance=distance
        )
        created_collection = rag_repository.create_collection(collection)
        return created_collection
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create collection: {str(e)}")

@router.get("/collections/board/{board_id}", response_model=List[RAGCollection])
async def get_collections_by_board(
    board_id: int,
    user_id: int = Depends(check_trial_active)
):
    # Verify board ownership
    await verify_board_access(board_id, user_id)
    
    collections = rag_repository.get_collections_by_board(board_id)
    return collections

@router.get("/collections/{collection_id}", response_model=RAGCollection)
async def get_collection(
    collection_id: int,
    user_id: int = Depends(check_trial_active)
):
    collection = await verify_collection_access(collection_id, user_id)
    return collection

@router.delete("/collections/{collection_id}")
async def delete_collection(
    collection_id: int,
    user_id: int = Depends(check_trial_active)
):
    collection = await verify_collection_access(collection_id, user_id)
    
    try:
        success = rag_repository.delete_collection(collection_id)
        if success:
            return {"message": f"Collection '{collection.collection_name}' deleted successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete collection")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting collection: {str(e)}")

# Document management
@router.post("/collections/{collection_id}/documents")
async def upload_document(
    collection_id: int,
    file: UploadFile = File(...),
    metadata: str = Form("{}"),
    user_id: int = Depends(check_trial_active)
):
    collection = await verify_collection_access(collection_id, user_id)
    
    try:
        # Parse metadata
        metadata_dict = json.loads(metadata)
        
        # Save the file temporarily
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        try:
            content = await file.read()
            temp_file.write(content)
            temp_file.close()
            
            # Submit the job
            job_id = rag_repository.submit_document_job(
                collection_id=collection_id,
                file_path=temp_file.name,
                filename=file.filename,
                metadata=metadata_dict
            )
            
            return {
                "job_id": job_id,
                "status": "queued",
                "filename": file.filename
            }
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

@router.get("/collections/{collection_id}/files", response_model=List[FileInfo])
async def list_files(
    collection_id: int,
    prefix: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    user_id: int = Depends(check_trial_active)
):
    await verify_collection_access(collection_id, user_id)
    
    try:
        files = rag_repository.list_files(collection_id, prefix, limit)
        return files
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing files: {str(e)}")

@router.delete("/collections/{collection_id}/files/{filename}")
async def delete_file(
    collection_id: int,
    filename: str,
    delete_vectors: bool = Query(True),
    user_id: int = Depends(check_trial_active)
):
    await verify_collection_access(collection_id, user_id)
    
    try:
        rag_repository.delete_file(collection_id, filename, delete_vectors)
        return {"message": f"File '{filename}' deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")

# Chat functionality
@router.post("/collections/{collection_id}/chat")
async def chat_with_collection(
    collection_id: int,
    message: str = Form(...),
    session_id: Optional[str] = Form(None),
    user_id: int = Depends(check_trial_active)
):
    await verify_collection_access(collection_id, user_id)
    
    try:
        response = rag_repository.chat(collection_id, message, session_id)
        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}")

@router.get("/collections/{collection_id}/chat/history", response_model=List[ChatMessage])
async def get_chat_history(
    collection_id: int,
    session_id: Optional[str] = None,
    user_id: int = Depends(check_trial_active)
):
    await verify_collection_access(collection_id, user_id)
    
    try:
        messages = rag_repository.get_chat_history(collection_id, session_id)
        return messages
    except ValueError as e:
        messages = rag_repository.get_chat_history(collection_id, session_id)
        return messages
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving chat history: {str(e)}")

@router.get("/collections/{collection_id}/chat/sessions", response_model=List[ChatSession])
async def get_chat_sessions(
    collection_id: int,
    user_id: int = Depends(check_trial_active)
):
    await verify_collection_access(collection_id, user_id)
    
    try:
        sessions = rag_repository.get_chat_sessions(collection_id)
        return sessions
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving chat sessions: {str(e)}")

@router.delete("/collections/{collection_id}/chat/{session_id}")
async def delete_chat_session(
    collection_id: int,
    session_id: str,
    user_id: int = Depends(check_trial_active)
):
    await verify_collection_access(collection_id, user_id)
    
    try:
        deleted_count = rag_repository.delete_chat_history(collection_id, session_id)
        if deleted_count == 0:
            raise HTTPException(status_code=404, detail="Chat session not found")
            
        return {
            "message": f"Successfully deleted chat session with {deleted_count} messages",
            "deleted_count": deleted_count
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting chat session: {str(e)}")

@router.get("/collections/{collection_id}/chat/stats", response_model=ChatStats)
async def get_chat_stats(
    collection_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    user_id: int = Depends(check_trial_active)
):
    await verify_collection_access(collection_id, user_id)
    
    try:
        stats = rag_repository.get_chat_stats(collection_id, start_date, end_date)
        return stats
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving chat statistics: {str(e)}")

@router.get("/collections/{collection_id}/chat/search")
async def search_chat_history(
    collection_id: int,
    query: str,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_id: int = Depends(check_trial_active)
):
    await verify_collection_access(collection_id, user_id)
    
    try:
        # Get all chat history
        all_messages = rag_repository.get_chat_history(collection_id)
        
        # Filter messages containing the query string (case-insensitive)
        matching_messages = [
            msg for msg in all_messages 
            if query.lower() in msg.message.lower()
        ]
        
        # Apply pagination
        paginated_messages = matching_messages[offset:offset + limit]
        
        return {
            "messages": paginated_messages,
            "total_count": len(matching_messages),
            "offset": offset,
            "limit": limit
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching chat history: {str(e)}")

@router.get("/collections/{collection_id}/chat/export")
async def export_chat_history(
    collection_id: int,
    session_id: str,
    format: str = Query("json", regex="^(json|text)$"),
    user_id: int = Depends(check_trial_active)
):
    await verify_collection_access(collection_id, user_id)
    
    try:
        messages = rag_repository.get_chat_history(collection_id, session_id)
        if not messages:
            raise HTTPException(status_code=404, detail="Chat session not found")
            
        collection = rag_repository.get_collection(collection_id)
        
        if format.lower() == "json":
            return {
                "session_id": session_id,
                "collection_name": collection.collection_name,
                "messages": messages
            }
        elif format.lower() == "text":
            from fastapi.responses import PlainTextResponse
            
            chat_text = "\n\n".join([
                f"[{msg.timestamp.isoformat()}] {msg.sender}:\n{msg.message}"
                for msg in messages
            ])
            
            return PlainTextResponse(chat_text)
        else:
            raise HTTPException(status_code=400, detail="Unsupported export format")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting chat history: {str(e)}")