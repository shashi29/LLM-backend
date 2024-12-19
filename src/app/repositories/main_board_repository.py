from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy import text
from app.repositories.base_repository import BaseRepository
from app.models.main_board import MainBoard
from app.repositories.access_control_repository import AccessControlRepository
import json

class MainBoardRepository(BaseRepository):
    def __init__(self):
        super().__init__('MainBoard')
        self.access_control_repo = AccessControlRepository()
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

    def create_main_board(self, user_id: int, main_board: MainBoard) -> Any:
        if not self.access_control_repo.check_permission(user_id, 0, 'MainBoard', 'create'):
            raise PermissionError("User does not have create access.")

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

        # Grant default permissions to the creator
        permission = {
            "view": True, "update": True, "delete": True
        }
        self.access_control_repo.grant_permissions(user_id, main_board_instance.id, 'MainBoard', permission)

        return main_board_instance

    def get_main_board(self, user_id: int, main_board_id: int) -> Any:
        if not self.access_control_repo.check_permission(user_id, main_board_id, 'MainBoard', 'view'):
            return None

        query = text("""
            SELECT * FROM MainBoard WHERE id = :main_board_id;
        """)
        values = {"main_board_id": main_board_id}
        main_board_data_tuple = self.execute_query(query, values)
        main_board_instance = MainBoard(**dict(zip(MainBoard.__annotations__, main_board_data_tuple)))
        return main_board_instance

    def get_all_main_boards(self, user_id: int) -> Any:
        if not self.access_control_repo.check_permission(user_id, 0, 'MainBoard', 'view'):
            # raise PermissionError("User does not have view access.")
            return None
        
        query = text("""
            SELECT * FROM MainBoard;
        """)
        main_boards_data_list = self.execute_query_all(query)
        main_boards = [MainBoard(**dict(zip(MainBoard.__annotations__, main_board_data))) for main_board_data in main_boards_data_list]
        return main_boards

    def update_main_board(self, user_id: int, main_board_id: int, main_board: MainBoard) -> Any:
        if not self.access_control_repo.check_permission(user_id, main_board_id, 'MainBoard', 'update'):
            raise PermissionError("User does not have update access.")

        query = text("""
            UPDATE MainBoard
            SET client_user_id = :client_user_id, name = :name, updated_at = CURRENT_TIMESTAMP
            WHERE id = :main_board_id
            RETURNING id, client_user_id, name, created_at, updated_at;
        """)
        values = {
            "client_user_id": main_board.client_user_id,
            "name": main_board.name,
            "main_board_id": main_board_id
        }
        main_board_data_tuple = self.execute_query(query, values)
        main_board_instance = MainBoard(**dict(zip(MainBoard.__annotations__, main_board_data_tuple)))
        return main_board_instance

    def delete_main_board(self, user_id: int, main_board_id: int) -> Any:
        if not self.access_control_repo.check_permission(user_id, 0, 'MainBoard', 'delete'):
            raise PermissionError("User does not have delete access.")

        query = text("""
            DELETE FROM MainBoard WHERE id = :main_board_id
            RETURNING id, client_user_id, name, created_at, updated_at;
        """)
        values = {"main_board_id": main_board_id}
        main_board_data_tuple = self.execute_query(query, values)
        main_board_instance = MainBoard(**dict(zip(MainBoard.__annotations__, main_board_data_tuple)))

        # Revoke permissions for this board
        self.access_control_repo.revoke_permissions(user_id, main_board_id, 'MainBoard')

        return main_board_instance

    def convert_to_tree_structure(self, data: List[Tuple[int, str, Optional[int], str]]) -> List[Dict[str, Any]]:
        tree = {}

        for item in data:
            main_board_id, client_user_id, main_board_name, main_board_type, board_id, board_name, is_active = item

            if main_board_id not in tree:
                tree[main_board_id] = {
                    "main_board_id": main_board_id,
                    "client_user_id": client_user_id,
                    "name": main_board_name,
                    "main_board_type": main_board_type,
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

    def get_all_info_tree(self, user_id: int) -> Any:
        # Check if the user has view access to MainBoard
        if not self.access_control_repo.check_permission(user_id, 0, 'MainBoard', 'view'):
            raise PermissionError("User does not have access to view MainBoard information.")

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