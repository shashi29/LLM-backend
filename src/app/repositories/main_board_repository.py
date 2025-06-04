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
        main_board_instance = MainBoard(**dict(zip(MainBoard.__annotations__, main_board_data_tuple)))
        return main_board_instance

    def delete_main_board(self, main_board_id: int) -> Any:
        # First, delete all boards associated with this main board
        self.delete_boards_for_main_board(main_board_id)
        
        # Then delete the main board itself
        query = text("""
            DELETE FROM MainBoard WHERE id = :main_board_id
            RETURNING id, client_user_id, name, main_board_type, created_at, updated_at;
        """)
        values = {"main_board_id": main_board_id}
        main_board_data_tuple = self.execute_query(query, values)
        main_board_instance = MainBoard(**dict(zip(MainBoard.__annotations__, main_board_data_tuple)))
        return main_board_instance
    
    def delete_boards_for_main_board(self, main_board_id: int) -> None:
        """Delete all boards associated with a main board."""
        # First, find all boards for this main board
        query = text("""
            SELECT id FROM Boards WHERE main_board_id = :main_board_id;
        """)
        values = {"main_board_id": main_board_id}
        board_ids = self.execute_query_all(query, values)
        
        # For each board, delete associated records (prompts, AI documentation, data tables)
        for board_id in board_ids:
            if board_id:
                # Delete prompts
                query = text("""
                    DELETE FROM Prompts WHERE board_id = :board_id;
                """)
                self.execute_query(query, {"board_id": board_id[0]})
                
                # Delete AI documentation
                query = text("""
                    DELETE FROM AiDocumentation WHERE board_id = :board_id;
                """)
                self.execute_query(query, {"board_id": board_id[0]})
                
                # Delete data management tables and their associated table statuses
                query = text("""
                    SELECT id FROM DataManagementTable WHERE board_id = :board_id;
                """)
                data_table_ids = self.execute_query_all(query, {"board_id": board_id[0]})
                
                for data_table_id in data_table_ids:
                    if data_table_id:
                        query = text("""
                            DELETE FROM TableStatus WHERE data_management_table_id = :data_table_id;
                        """)
                        self.execute_query(query, {"data_table_id": data_table_id[0]})
                
                query = text("""
                    DELETE FROM DataManagementTable WHERE board_id = :board_id;
                """)
                self.execute_query(query, {"board_id": board_id[0]})
        
        # Finally, delete all boards for this main board
        query = text("""
            DELETE FROM Boards WHERE main_board_id = :main_board_id;
        """)
        self.execute_query(query, {"main_board_id": main_board_id})

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