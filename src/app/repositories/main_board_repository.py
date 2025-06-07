from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy import text
from app.repositories.base_repository import BaseRepository
from app.models.main_board import MainBoard

class MainBoardRepository(BaseRepository):
    def __init__(self):
        super().__init__('MainBoard')
        create_table_query = text("""
            CREATE TABLE IF NOT EXISTS MainBoard (
                id SERIAL PRIMARY KEY,
                client_user_id INT REFERENCES ClientUsers(id),
                name VARCHAR UNIQUE,
                main_board_type VARCHAR,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            );
        """)
        self.create_table(create_table_query)

    def create_main_board(self, main_board: MainBoard) -> Any:
        query = text("""
            INSERT INTO MainBoard (client_user_id, name, main_board_type, created_at, updated_at)
            VALUES (:client_user_id, :name, :main_board_type, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id, client_user_id, name, main_board_type, created_at, updated_at;
        """)
        values = {
            "client_user_id": main_board.client_user_id,
            "name": main_board.name,
            "main_board_type": main_board.main_board_type
        }
        main_board_data_tuple = self.execute_query(query, values)
        main_board_instance = MainBoard(**dict(zip(MainBoard.__annotations__, main_board_data_tuple)))
        return main_board_instance

    def get_main_board(self, main_board_id: int) -> Any:
        query = text("""
            SELECT * FROM MainBoard WHERE id = :main_board_id;
        """)
        values = {"main_board_id": main_board_id}
        main_board_data_tuple = self.execute_query(query, values)
        if not main_board_data_tuple:
            return None
        main_board_instance = MainBoard(**dict(zip(MainBoard.__annotations__, main_board_data_tuple)))
        return main_board_instance

    def get_all_main_boards(self) -> Any:
        query = text("""
            SELECT * FROM MainBoard;
        """)
        main_boards_data_list = self.execute_query_all(query)
        main_boards = [MainBoard(**dict(zip(MainBoard.__annotations__, main_board_data))) for main_board_data in main_boards_data_list]
        return main_boards
        
    def get_main_boards_by_user(self, user_id: int) -> Any:
        """Get all main boards for a specific user."""
        query = text("""
            SELECT * FROM MainBoard WHERE client_user_id = :user_id;
        """)
        values = {"user_id": user_id}
        main_boards_data_list = self.execute_query_all(query, values)
        main_boards = [MainBoard(**dict(zip(MainBoard.__annotations__, main_board_data))) for main_board_data in main_boards_data_list]
        return main_boards

    def update_main_board(self, main_board_id: int, main_board: MainBoard) -> Any:
        query = text("""
            UPDATE MainBoard
            SET client_user_id = :client_user_id, name = :name, updated_at = CURRENT_TIMESTAMP
            WHERE id = :main_board_id
            RETURNING id, client_user_id, name, main_board_type, created_at, updated_at;
        """)
        values = {
            "client_user_id": main_board.client_user_id,
            "name": main_board.name,
            "main_board_id": main_board_id
        }
        main_board_data_tuple = self.execute_query(query, values)
        if not main_board_data_tuple:
            return None
        main_board_instance = MainBoard(**dict(zip(MainBoard.__annotations__, main_board_data_tuple)))
        return main_board_instance

    def delete_main_board(self, main_board_id: int) -> Any:
        # Get the main board details before deletion
        main_board = self.get_main_board(main_board_id)
        if not main_board:
            return None
            
        # Delete everything in the correct order
        self.delete_boards_for_main_board(main_board_id)
        
        # Finally, delete the main board itself
        query = text("""
            DELETE FROM MainBoard WHERE id = :main_board_id;
        """)
        values = {"main_board_id": main_board_id}
        self.execute_delete_query(query, values)
        
        return main_board  # Return the main board that was deleted
    
    def delete_boards_for_main_board(self, main_board_id: int) -> None:
        """Delete all boards associated with a main board and their related data."""
        # First, get all board IDs for this main board
        query = text("""
            SELECT id FROM Boards WHERE main_board_id = :main_board_id;
        """)
        values = {"main_board_id": main_board_id}
        board_results = self.execute_query_all(query, values)
        
        # Extract board IDs from results
        board_ids = [result[0] for result in board_results if result]
        
        # For each board, delete all related data in the correct order
        for board_id in board_ids:
            self.delete_board_related_data(board_id)
        
        # Finally, delete all boards for this main board
        query = text("""
            DELETE FROM Boards WHERE main_board_id = :main_board_id;
        """)
        values = {"main_board_id": main_board_id}
        self.execute_delete_query(query, values)
    
    def delete_board_related_data(self, board_id: int) -> None:
        """Delete all data related to a specific board in the correct order."""
        
        print(f"Deleting related data for board_id: {board_id}")
        
        # 1. Delete prompt responses first (they reference prompts and boards)
        try:
            query = text("""
                DELETE FROM Prompts_response WHERE board_id = :board_id;
            """)
            self.execute_delete_query(query, {"board_id": board_id})
            print(f"Deleted prompt responses for board {board_id}")
        except Exception as e:
            print(f"Warning: Could not delete from Prompts_response: {e}")
        
        # 2. Delete prompts (they reference boards)
        try:
            query = text("""
                DELETE FROM Prompts WHERE board_id = :board_id;
            """)
            self.execute_delete_query(query, {"board_id": board_id})
            print(f"Deleted prompts for board {board_id}")
        except Exception as e:
            print(f"Warning: Could not delete prompts: {e}")
        
        # 3. Delete AI documentation (references boards)
        try:
            query = text("""
                DELETE FROM AiDocumentation WHERE board_id = :board_id;
            """)
            self.execute_delete_query(query, {"board_id": board_id})
            print(f"Deleted AI documentation for board {board_id}")
        except Exception as e:
            print(f"Warning: Could not delete AI documentation: {e}")
        
        # 4. Delete RAG collections and their chat messages (if RAG tables exist)
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
                    self.execute_delete_query(query, {"collection_id": rag_collection_id})
                    print(f"Deleted chat messages for RAG collection {rag_collection_id}")
            
            # Delete RAG collections
            query = text("""
                DELETE FROM RAGCollection WHERE board_id = :board_id;
            """)
            self.execute_delete_query(query, {"board_id": board_id})
            print(f"Deleted RAG collections for board {board_id}")
        except Exception as e:
            print(f"Warning: Could not delete RAG data: {e}")
        
        # 5. Delete table statuses first, then data management tables
        try:
            # Get all data management table IDs for this board
            query = text("""
                SELECT id FROM DataManagementTable WHERE board_id = :board_id;
            """)
            data_table_results = self.execute_query_all(query, {"board_id": board_id})
            
            # Delete table statuses for each data management table
            for data_result in data_table_results:
                if data_result:
                    data_table_id = data_result[0]
                    query = text("""
                        DELETE FROM TableStatus WHERE data_management_table_id = :data_table_id;
                    """)
                    self.execute_delete_query(query, {"data_table_id": data_table_id})
                    print(f"Deleted table statuses for data table {data_table_id}")
            
            # Delete data management tables
            query = text("""
                DELETE FROM DataManagementTable WHERE board_id = :board_id;
            """)
            self.execute_delete_query(query, {"board_id": board_id})
            print(f"Deleted data management tables for board {board_id}")
        except Exception as e:
            print(f"Warning: Could not delete data management tables: {e}")
        
        # 6. Check for any other tables that might reference boards
        self.delete_any_remaining_board_references(board_id)
        
        print(f"Completed deletion of related data for board {board_id}")
    
    def delete_any_remaining_board_references(self, board_id: int) -> None:
        """Delete any remaining references to the board from other tables."""
        
        # List of potential tables that might reference boards
        # Add any other tables that reference boards in your system
        potential_tables = [
            "time_line_settings",  # if this table exists
            "board_settings",      # if this table exists
            "user_board_access",   # if this table exists
        ]
        
        for table_name in potential_tables:
            try:
                # Try to delete from each potential table
                query = text(f"""
                    DELETE FROM {table_name} WHERE board_id = :board_id;
                """)
                self.execute_delete_query(query, {"board_id": board_id})
                print(f"Deleted from {table_name} for board {board_id}")
            except Exception as e:
                # Table might not exist or might not have board_id column
                print(f"Skipping {table_name}: {e}")
                continue
    
    def execute_delete_query(self, query, values=None):
        """Execute a DELETE query without expecting return values."""
        connection = self.get_database_connection()
        try:
            with connection.connect() as cursor:
                cursor.execute(query, values)
                cursor.commit()
        finally:
            connection.dispose()

    def convert_to_tree_structure(self, data: List[Tuple[int, str, Optional[int], str]]) -> List[Dict[str, Any]]:
        tree = {}

        for item in data:
            main_board_id, client_user_id, main_board_name, main_board_type, board_id, board_name, is_active = item

            if main_board_id not in tree:
                tree[main_board_id] = {
                    "main_board_id":main_board_id,
                    "client_user_id": client_user_id,
                    "name": main_board_name,
                    "main_board_type":main_board_type,
                    "is_selected": False,
                    "boards": {}
                }

            if board_id is not None and board_id not in tree[main_board_id]["boards"]:
                tree[main_board_id]["boards"][board_id] = {
                    "name": board_name,
                    "is_active": is_active,
                    "is_selected": False
                }

        return list(tree.values())

    def get_all_info_tree(self) -> Any:
        query = text("""
                        SELECT
                            mb.id AS main_board_id,
                            mb.client_user_id AS client_user_id,
                            mb.name AS main_board_name,
                            mb.main_board_type AS main_board_type,
                            b.id AS board_id,
                            b.name AS board_name,
                            b.is_active AS is_active
                        FROM
                            MainBoard mb
                        LEFT JOIN
                            Boards b ON mb.id = b.main_board_id;
                    """)
        all_info_tree = self.execute_query_all(query)
        tree_output = self.convert_to_tree_structure(all_info_tree)
        return tree_output
    
    def get_user_info_tree(self, user_id: int) -> Any:
        """Get information tree for a specific user."""
        query = text("""
                        SELECT
                            mb.id AS main_board_id,
                            mb.client_user_id AS client_user_id,
                            mb.name AS main_board_name,
                            mb.main_board_type AS main_board_type,
                            b.id AS board_id,
                            b.name AS board_name,
                            b.is_active AS is_active
                        FROM
                            MainBoard mb
                        LEFT JOIN
                            Boards b ON mb.id = b.main_board_id
                        WHERE
                            mb.client_user_id = :user_id;
                    """)
        values = {"user_id": user_id}
        user_info_tree = self.execute_query_all(query, values)
        tree_output = self.convert_to_tree_structure(user_info_tree)
        return tree_output
    
    def is_main_board_owned_by_user(self, main_board_id: int, user_id: int) -> bool:
        """Check if a main board is owned by a specific user."""
        query = text("""
            SELECT id FROM MainBoard 
            WHERE id = :main_board_id AND client_user_id = :user_id;
        """)
        values = {"main_board_id": main_board_id, "user_id": user_id}
        result = self.execute_query(query, values)
        return bool(result)

    def get_database_connection(self):
        """Get database connection from the base repository."""
        from app.database import get_database_connection
        return get_database_connection()