# app/repositories/boards_repository.py

from typing import Any, List, Optional
from sqlalchemy import text
from app.repositories.base_repository import BaseRepository
from app.models.boards import Boards
from app.database import get_database_connection

class BoardsRepository(BaseRepository):
    def __init__(self):
        super().__init__('Boards')
        create_table_query = text("""
            CREATE TABLE IF NOT EXISTS Boards (
                id SERIAL PRIMARY KEY,
                main_board_id INT REFERENCES MainBoard(id),
                name VARCHAR(255),
                is_active BOOLEAN,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            );
        """)
        self.create_table(create_table_query)
        
    def create_board(self, board: Boards) -> Any:
        query = text("""
            INSERT INTO Boards (main_board_id, name, is_active, created_at, updated_at)
            VALUES (:main_board_id, :name, :is_active, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id, main_board_id, name, is_active, created_at, updated_at;
        """)

        values = {
            "main_board_id": board.main_board_id,
            "name": board.name,
            "is_active": board.is_active if hasattr(board, 'is_active') and board.is_active is not None else True,
        }

        board_data_tuple = self.execute_query(query, values)
        if not board_data_tuple:
            return None
            
        board_dict = {
            "id": board_data_tuple[0],
            "main_board_id": board_data_tuple[1],
            "name": board_data_tuple[2],
            "is_active": board_data_tuple[3],
            "created_at": board_data_tuple[4],
            "updated_at": board_data_tuple[5]
        }
        
        board_instance = Boards(**board_dict)
        return board_instance

    def get_boards(self) -> List[Boards]:
        query = text("""
            SELECT id, main_board_id, name, is_active, created_at, updated_at
            FROM Boards;
        """)

        board_data_list = self.execute_query_all(query)
        board_list = []
        
        for board_data in board_data_list:
            if board_data:
                board_dict = {
                    "id": board_data[0],
                    "main_board_id": board_data[1],
                    "name": board_data[2],
                    "is_active": board_data[3],
                    "created_at": board_data[4],
                    "updated_at": board_data[5]
                }
                board_list.append(Boards(**board_dict))
                
        return board_list

    def get_board(self, board_id: int) -> Optional[Boards]:
        query = text("""
            SELECT id, main_board_id, name, is_active, created_at, updated_at
            FROM Boards WHERE id = :board_id;
        """)

        values = {"board_id": board_id}

        board_data_tuple = self.execute_query(query, values)
        
        # Add debug logging
        print(f"get_board query result for board_id={board_id}: {board_data_tuple}")
        
        if not board_data_tuple:
            print(f"No board found with id {board_id}")
            return None
            
        try:
            board_dict = {
                "id": board_data_tuple[0],
                "main_board_id": board_data_tuple[1],
                "name": board_data_tuple[2],
                "is_active": board_data_tuple[3],
                "created_at": board_data_tuple[4],
                "updated_at": board_data_tuple[5]
            }
            
            board_instance = Boards(**board_dict)
            print(f"Successfully created board instance: {board_instance}")
            return board_instance
            
        except Exception as e:
            print(f"Error creating board instance: {e}")
            print(f"Data received: {board_data_tuple}")
            return None

    def update_board(self, board_id: int, board: Boards) -> Optional[Boards]:
        query = text("""
            UPDATE Boards
            SET main_board_id = :main_board_id,
                name = :name,
                is_active = :is_active,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = :board_id
            RETURNING id, main_board_id, name, is_active, created_at, updated_at;
        """)

        values = {
            "main_board_id": board.main_board_id,
            "name": board.name,
            "is_active": board.is_active if hasattr(board, 'is_active') and board.is_active is not None else True,
            "board_id": board_id
        }

        board_data_tuple = self.execute_query(query, values)
        if not board_data_tuple:
            return None
            
        board_dict = {
            "id": board_data_tuple[0],
            "main_board_id": board_data_tuple[1],
            "name": board_data_tuple[2],
            "is_active": board_data_tuple[3],
            "created_at": board_data_tuple[4],
            "updated_at": board_data_tuple[5]
        }
        
        board_instance = Boards(**board_dict)
        return board_instance

    def delete_board(self, board_id: int) -> Optional[Boards]:
        # Get the board details before deletion
        board = self.get_board(board_id)
        if not board:
            return None
        
        # Delete related records in the correct order
        # 1. Delete prompt responses first
        try:
            query = text("""
                DELETE FROM Prompts_response WHERE board_id = :board_id;
            """)
            connection = get_database_connection()
            try:
                with connection.connect() as cursor:
                    cursor.execute(query, {"board_id": board_id})
                    cursor.commit()
            finally:
                connection.dispose()
        except Exception as e:
            print(f"Warning: Could not delete prompt responses: {e}")
        
        # 2. Delete prompts
        query = text("""
            DELETE FROM Prompts WHERE board_id = :board_id;
        """)
        connection = get_database_connection()
        try:
            with connection.connect() as cursor:
                cursor.execute(query, {"board_id": board_id})
                cursor.commit()
        finally:
            connection.dispose()
        
        # 3. Delete AI documentation
        query = text("""
            DELETE FROM AiDocumentation WHERE board_id = :board_id;
        """)
        connection = get_database_connection()
        try:
            with connection.connect() as cursor:
                cursor.execute(query, {"board_id": board_id})
                cursor.commit()
        finally:
            connection.dispose()
        
        # 4. Delete RAG collections and their chat messages (if they exist)
        try:
            # First get RAG collection IDs
            query = text("""
                SELECT id FROM RAGCollection WHERE board_id = :board_id;
            """)
            rag_collection_results = self.execute_query_all(query, {"board_id": board_id})
            
            # Delete chat messages for each RAG collection
            for rag_result in rag_collection_results:
                if rag_result:
                    rag_collection_id = rag_result[0]
                    query = text("""
                        DELETE FROM ChatMessage WHERE collection_id = :collection_id;
                    """)
                    connection = get_database_connection()
                    try:
                        with connection.connect() as cursor:
                            cursor.execute(query, {"collection_id": rag_collection_id})
                            cursor.commit()
                    finally:
                        connection.dispose()
            
            # Delete RAG collections
            query = text("""
                DELETE FROM RAGCollection WHERE board_id = :board_id;
            """)
            connection = get_database_connection()
            try:
                with connection.connect() as cursor:
                    cursor.execute(query, {"board_id": board_id})
                    cursor.commit()
            finally:
                connection.dispose()
        except Exception as e:
            print(f"Warning: Could not delete RAG data: {e}")
        
        # 5. Delete data management tables and their associated table statuses
        query = text("""
            SELECT id FROM DataManagementTable WHERE board_id = :board_id;
        """)
        data_table_ids = self.execute_query_all(query, {"board_id": board_id})
        
        for data_table_id in data_table_ids:
            if data_table_id:
                query = text("""
                    DELETE FROM TableStatus WHERE data_management_table_id = :data_table_id;
                """)
                connection = get_database_connection()
                try:
                    with connection.connect() as cursor:
                        cursor.execute(query, {"data_table_id": data_table_id[0]})
                        cursor.commit()
                finally:
                    connection.dispose()
        
        query = text("""
            DELETE FROM DataManagementTable WHERE board_id = :board_id;
        """)
        connection = get_database_connection()
        try:
            with connection.connect() as cursor:
                cursor.execute(query, {"board_id": board_id})
                cursor.commit()
        finally:
            connection.dispose()
        
        # Finally, delete the board itself
        query = text("""
            DELETE FROM Boards WHERE id = :board_id;
        """)
        connection = get_database_connection()
        try:
            with connection.connect() as cursor:
                cursor.execute(query, {"board_id": board_id})
                cursor.commit()
        finally:
            connection.dispose()
        
        return board  # Return the board that was deleted
    
    def get_boards_for_main_boards(self, main_board_id: int) -> List[Boards]:
        query = text("""
            SELECT b.id, b.main_board_id, b.name, b.is_active, b.created_at, b.updated_at
            FROM Boards b
            JOIN MainBoard m ON b.main_board_id = m.id
            WHERE m.id = :main_board_id;
        """)

        values = {"main_board_id": main_board_id}

        board_data_list = self.execute_query_all(query, values)
        board_list = []
        
        for board_data in board_data_list:
            if board_data:
                board_dict = {
                    "id": board_data[0],
                    "main_board_id": board_data[1],
                    "name": board_data[2],
                    "is_active": board_data[3],
                    "created_at": board_data[4],
                    "updated_at": board_data[5]
                }
                board_list.append(Boards(**board_dict))
                
        return board_list
    
    def is_board_owned_by_user(self, board_id: int, user_id: int) -> bool:
        """Check if a board is owned by a specific user through its main board."""
        query = text("""
            SELECT b.id 
            FROM Boards b
            JOIN MainBoard mb ON b.main_board_id = mb.id
            WHERE b.id = :board_id AND mb.client_user_id = :user_id;
        """)
        values = {"board_id": board_id, "user_id": user_id}
        
        # Add debug logging
        print(f"Checking ownership for board_id={board_id}, user_id={user_id}")
        
        result = self.execute_query(query, values)
        print(f"Ownership query result: {result}")
        
        is_owned = bool(result)
        print(f"Board {board_id} owned by user {user_id}: {is_owned}")
        
        return is_owned

    def update_board_timestamp(self, board_id: int) -> None:
        query = text("""
            UPDATE Boards
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = :board_id;
        """)

        values = {"board_id": board_id}
        self.execute_query(query, values)
        
    def debug_board_info(self, board_id: int):
        """Debug method to get detailed board information."""
        # First, check if board exists
        board_query = text("""
            SELECT id, main_board_id, name, is_active, created_at, updated_at
            FROM Boards WHERE id = :board_id;
        """)
        board_result = self.execute_query(board_query, {"board_id": board_id})
        
        # Get main board info if board exists
        main_board_info = None
        if board_result:
            main_board_query = text("""
                SELECT id, client_user_id, name, main_board_type
                FROM MainBoard WHERE id = :main_board_id;
            """)
            main_board_info = self.execute_query(main_board_query, {"main_board_id": board_result[1]})
        
        return {
            "board_exists": bool(board_result),
            "board_data": board_result,
            "main_board_data": main_board_info,
            "raw_query_result": board_result
        }