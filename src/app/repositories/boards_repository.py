from typing import Any, List, Dict
from sqlalchemy import text
from app.repositories.base_repository import BaseRepository
from app.models.boards import Boards
from app.repositories.access_control_repository import AccessControlRepository


class BoardsRepository(BaseRepository):
    def __init__(self):
        super().__init__('Boards')
        self.access_control_repo = AccessControlRepository()
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

    def create_board(self, user_id: int, board: Boards) -> Any:
        # Check permissions
        if not self.access_control_repo.check_permission(user_id, board.main_board_id, 'Boards', 'create'):
            raise PermissionError("User does not have create access.")

        query = text("""
            INSERT INTO Boards (main_board_id, name, created_at, updated_at, is_active)
            VALUES (:main_board_id, :name, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, :is_active)
            RETURNING id, main_board_id, name, created_at, updated_at, is_active;
        """)

        values = {
            "main_board_id": board.main_board_id,
            "name": board.name,
            "is_active": board.is_active if hasattr(board, 'is_active') else True,
        }

        board_data_tuple = self.execute_query(query, values)
        board_instance = Boards(**dict(zip(Boards.__annotations__, board_data_tuple)))

        # Grant default permissions to the creator
        permission = {
            "view": True, "update": True, "delete": True
        }
        self.access_control_repo.grant_permissions(user_id, board_instance.id, 'Boards', permission)

        return board_instance

    def get_board(self, user_id: int, board_id: int) -> Any:
        # Check permissions
        if not self.access_control_repo.check_permission(user_id, board_id, 'Boards', 'view'):
            return None

        query = text("""
            SELECT * FROM Boards WHERE id = :board_id;
        """)
        values = {"board_id": board_id}
        board_data_tuple = self.execute_query(query, values)
        board_instance = Boards(**dict(zip(Boards.__annotations__, board_data_tuple)))
        return board_instance

    def get_all_boards(self, user_id: int) -> List[Boards]:
        # Check permissions
        if not self.access_control_repo.check_permission(user_id, 0, 'Boards', 'view'):
            raise PermissionError("User does not have view access.")

        query = text("""
            SELECT * FROM Boards WHERE is_active = TRUE;
        """)
        board_data_list = self.execute_query_all(query)
        boards = [Boards(**dict(zip(Boards.__annotations__, board_data))) for board_data in board_data_list]
        return boards

    def update_board(self, user_id: int, board_id: int, board: Boards) -> Any:
        # Check permissions
        if not self.access_control_repo.check_permission(user_id, board_id, 'Boards', 'update'):
            raise PermissionError("User does not have update access.")

        query = text("""
            UPDATE Boards
            SET main_board_id = :main_board_id,
                name = :name,
                is_active = :is_active,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = :board_id
            RETURNING id, main_board_id, name, created_at, updated_at, is_active;
        """)
        values = {
            "main_board_id": board.main_board_id,
            "name": board.name,
            "is_active": board.is_active,
            "board_id": board_id
        }
        board_data_tuple = self.execute_query(query, values)
        board_instance = Boards(**dict(zip(Boards.__annotations__, board_data_tuple)))
        return board_instance

    def delete_board(self, user_id: int, board_id: int) -> Any:
        # Check permissions
        if not self.access_control_repo.check_permission(user_id, board_id, 'Boards', 'delete'):
            raise PermissionError("User does not have delete access.")

        query = text("""
            UPDATE Boards
            SET is_active = FALSE,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = :board_id
            RETURNING id, main_board_id, name, created_at, updated_at, is_active;
        """)
        values = {"board_id": board_id}
        board_data_tuple = self.execute_query(query, values)
        board_instance = Boards(**dict(zip(Boards.__annotations__, board_data_tuple)))

        # Revoke permissions
        self.access_control_repo.revoke_permissions(user_id, board_id, 'Boards')

        return board_instance

    def get_boards_for_main_board(self, user_id: int, main_board_id: int) -> List[Boards]:
        # Check permissions
        if not self.access_control_repo.check_permission(user_id, main_board_id, 'Boards', 'view'):
            raise PermissionError("User does not have view access for this main board.")

        query = text("""
            SELECT * FROM Boards WHERE main_board_id = :main_board_id AND is_active = TRUE;
        """)
        values = {"main_board_id": main_board_id}
        board_data_list = self.execute_query_all(query, values)
        boards = [Boards(**dict(zip(Boards.__annotations__, board_data))) for board_data in board_data_list]
        return boards
