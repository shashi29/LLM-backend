from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import text, func
from app.repositories.base_repository import BaseRepository
from app.models.rag_models import ChatHistory, ChatMessage, ChatSession

class ChatHistoryRepository(BaseRepository):
    def __init__(self):
        super().__init__('ChatHistory')
        create_table_query = text("""
            CREATE TABLE IF NOT EXISTS ChatHistory (
                id SERIAL PRIMARY KEY,
                session_id VARCHAR(255) NOT NULL,
                sender VARCHAR(50) NOT NULL,
                message TEXT NOT NULL,
                collection_id INTEGER REFERENCES RAGCollection(id) ON DELETE CASCADE,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        self.create_table(create_table_query)

    def save_message(self, message: ChatHistory) -> ChatHistory:
        query = text("""
            INSERT INTO ChatHistory (session_id, sender, message, collection_id, timestamp)
            VALUES (:session_id, :sender, :message, :collection_id, :timestamp)
            RETURNING id, session_id, sender, message, collection_id, timestamp;
        """)

        values = {
            "session_id": message.session_id,
            "sender": message.sender,
            "message": message.message,
            "collection_id": message.collection_id,
            "timestamp": message.timestamp or datetime.utcnow()
        }

        result = self.execute_query(query, values)
        return self._map_to_chat_history(result)

    def get_messages_by_session(self, session_id: str, collection_id: int) -> List[ChatHistory]:
        query = text("""
            SELECT id, session_id, sender, message, collection_id, timestamp
            FROM ChatHistory
            WHERE session_id = :session_id AND collection_id = :collection_id
            ORDER BY timestamp ASC;
        """)
        
        values = {"session_id": session_id, "collection_id": collection_id}
        results = self.execute_query_all(query, values)
        
        return [self._map_to_chat_history(result) for result in results]

    def get_messages_by_collection(self, collection_id: int) -> List[ChatHistory]:
        query = text("""
            SELECT id, session_id, sender, message, collection_id, timestamp
            FROM ChatHistory
            WHERE collection_id = :collection_id
            ORDER BY timestamp ASC;
        """)
        
        values = {"collection_id": collection_id}
        results = self.execute_query_all(query, values)
        
        return [self._map_to_chat_history(result) for result in results]

    def delete_session(self, session_id: str, collection_id: int) -> int:
        query = text("""
            DELETE FROM ChatHistory
            WHERE session_id = :session_id AND collection_id = :collection_id
            RETURNING id;
        """)
        
        values = {"session_id": session_id, "collection_id": collection_id}
        results = self.execute_query_all(query, values)
        
        return len(results)

    def get_sessions_by_collection(self, collection_id: int) -> List[ChatSession]:
        query = text("""
            SELECT 
                session_id, 
                MAX(timestamp) as last_message_time,
                COUNT(id) as message_count
            FROM ChatHistory
            WHERE collection_id = :collection_id
            GROUP BY session_id
            ORDER BY last_message_time DESC;
        """)
        
        values = {"collection_id": collection_id}
        results = self.execute_query_all(query, values)
        
        return [
            ChatSession(
                session_id=result[0],
                last_message=result[1].isoformat(),
                message_count=result[2]
            ) for result in results
        ]

    def search_messages(self, collection_id: int, query_text: str, limit: int = 10, offset: int = 0) -> (List[ChatHistory], int):
        search_query = text("""
            SELECT id, session_id, sender, message, collection_id, timestamp
            FROM ChatHistory
            WHERE collection_id = :collection_id AND message ILIKE :query_text
            ORDER BY timestamp DESC
            LIMIT :limit OFFSET :offset;
        """)
        
        count_query = text("""
            SELECT COUNT(*)
            FROM ChatHistory
            WHERE collection_id = :collection_id AND message ILIKE :query_text;
        """)
        
        values = {
            "collection_id": collection_id, 
            "query_text": f"%{query_text}%",
            "limit": limit,
            "offset": offset
        }
        
        results = self.execute_query_all(search_query, values)
        count_result = self.execute_query(count_query, {"collection_id": collection_id, "query_text": f"%{query_text}%"})
        
        messages = [self._map_to_chat_history(result) for result in results]
        total_count = count_result[0] if count_result else 0
        
        return messages, total_count

    def _map_to_chat_history(self, result) -> ChatHistory:
        return ChatHistory(
            id=result[0],
            session_id=result[1],
            sender=result[2],
            message=result[3],
            collection_id=result[4],
            timestamp=result[5]
        )