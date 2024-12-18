from typing import Any
from sqlalchemy import text
from app.repositories.base_repository import BaseRepository
from app.models.quadrant_collection import QuadrantCollectionTable

class QuadrantCollectionTableRepository(BaseRepository):
    def __init__(self):
        super().__init__('QuadrantCollectionTable')
        create_table_query = text("""
            CREATE TABLE IF NOT EXISTS QuadrantCollectionTable (
                id SERIAL PRIMARY KEY,
                board_id INT REFERENCES Boards(id),
                collection_name VARCHAR(255),
                collection_description TEXT,
                collection_configuration TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            );
        """)
        self.create_table(create_table_query)

    def create_quadrant_collection_table(self, quadrant_collection_table: QuadrantCollectionTable) -> Any:
        query = text("""
            INSERT INTO QuadrantCollectionTable (board_id, collection_name, collection_description, collection_configuration, created_at, updated_at)
            VALUES (:board_id, :collection_name, :collection_description, :collection_configuration, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id, board_id, collection_name, collection_description, collection_configuration, created_at, updated_at;
        """)

        values = {
            "board_id": quadrant_collection_table.board_id,
            "collection_name": quadrant_collection_table.collection_name,
            "collection_description": quadrant_collection_table.collection_description,
            "collection_configuration": quadrant_collection_table.collection_configuration,
        }

        quadrant_collection_table_data_tuple = self.execute_query(query, values)
        quadrant_collection_table_instance = QuadrantCollectionTable(**dict(zip(QuadrantCollectionTable.__annotations__, quadrant_collection_table_data_tuple)))
        return quadrant_collection_table_instance

    def get_all_quadrant_collection_table(self) -> Any:
        query = text("""
            SELECT * FROM QuadrantCollectionTable;
        """)

        quadrant_collection_table_data_list = self.execute_query_all(query)
        quadrant_collection_table_list = []

        for doc_data in quadrant_collection_table_data_list:
            quadrant_collection_table_instance = QuadrantCollectionTable(**dict(zip(QuadrantCollectionTable.__annotations__, doc_data)))
            try:
                quadrant_collection_table_instance.collection_configuration = eval(quadrant_collection_table_instance.collection_configuration)
            except Exception as ex:
                quadrant_collection_table_instance.collection_configuration = quadrant_collection_table_instance.collection_configuration
            quadrant_collection_table_list.append(quadrant_collection_table_instance)

        return quadrant_collection_table_list

    def get_quadrant_collection_table(self, doc_id: int) -> Any:
        query = text("""
            SELECT * FROM QuadrantCollectionTable WHERE id = :doc_id;
        """)

        values = {"doc_id": doc_id}

        quadrant_collection_table_data_tuple = self.execute_query(query, values)
        if quadrant_collection_table_data_tuple is None:
            return None
        quadrant_collection_table_instance = QuadrantCollectionTable(**dict(zip(QuadrantCollectionTable.__annotations__, quadrant_collection_table_data_tuple)))
        try:
            quadrant_collection_table_instance.collection_configuration = eval(quadrant_collection_table_instance.collection_configuration)
        except Exception as ex:
            quadrant_collection_table_instance.collection_configuration = quadrant_collection_table_instance.collection_configuration
        return quadrant_collection_table_instance

    def update_quadrant_collection_table(self, doc_id: int, quadrant_collection_table: QuadrantCollectionTable) -> Any:
        query = text("""
            UPDATE QuadrantCollectionTable
            SET board_id = :board_id, collection_name = :collection_name, collection_description = :collection_description, collection_configuration = :collection_configuration, updated_at = CURRENT_TIMESTAMP
            WHERE id = :doc_id
            RETURNING id, board_id, collection_name, collection_description, collection_configuration, created_at, updated_at;
        """)

        values = {
            "board_id": quadrant_collection_table.board_id,
            "collection_name": quadrant_collection_table.collection_name,
            "collection_description": quadrant_collection_table.collection_description,
            "collection_configuration": quadrant_collection_table.collection_configuration,
            "doc_id": doc_id
        }

        quadrant_collection_table_data_tuple = self.execute_query(query, values)
        if quadrant_collection_table_data_tuple is None:
            return quadrant_collection_table_data_tuple
        quadrant_collection_table_instance = QuadrantCollectionTable(**dict(zip(QuadrantCollectionTable.__annotations__, quadrant_collection_table_data_tuple)))
        return quadrant_collection_table_instance

    def delete_quadrant_collection_table(self, doc_id: int) -> Any:
        query = text("""
            DELETE FROM QuadrantCollectionTable WHERE id = :doc_id
            RETURNING id, board_id, collection_name, collection_description, collection_configuration, created_at, updated_at;
        """)

        values = {"doc_id": doc_id}

        quadrant_collection_table_data_tuple = self.execute_query(query, values)
        if quadrant_collection_table_data_tuple is None:
            return quadrant_collection_table_data_tuple
        quadrant_collection_table_instance = QuadrantCollectionTable(**dict(zip(QuadrantCollectionTable.__annotations__, quadrant_collection_table_data_tuple)))
        return quadrant_collection_table_instance

    def update_quadrant_collection_table_for_board(self, board_id: int, quadrant_collection_table: QuadrantCollectionTable) -> Any:
        """
        Update Quadrant Collection Table for a specific board.

        Args:
            board_id (int): The ID of the board for which Quadrant Collection Table needs to be updated.
            quadrant_collection_table (QuadrantCollectionTable): The Quadrant Collection Table object containing updated information.

        Returns:
            Any: Updated Quadrant Collection Table instance if successful, otherwise None.
        """
        # Check if Quadrant Collection Table exists for the provided board_id
        existing_table = self.get_quadrant_collection_table(board_id)
        
        if existing_table:
            # If Quadrant Collection Table exists, update it
            return self._update_existing_quadrant_collection_table(board_id, quadrant_collection_table)
        else: 
            # If Quadrant Collection Table doesn't exist, create a new one
            return self.create_quadrant_collection_table(quadrant_collection_table)

    def _update_existing_quadrant_collection_table(self, board_id: int, quadrant_collection_table: QuadrantCollectionTable) -> Any:
        """
        Update existing Quadrant Collection Table.

        Args:
            board_id (int): The ID of the Quadrant Collection Table to update.
            quadrant_collection_table (QuadrantCollectionTable): The Quadrant Collection Table object containing updated information.

        Returns:
            Any: Updated Quadrant Collection Table instance if successful, otherwise None.
        """
        query = text("""
            UPDATE QuadrantCollectionTable
            SET collection_name = :collection_name, collection_description = :collection_description, collection_configuration = :collection_configuration, updated_at = CURRENT_TIMESTAMP
            WHERE board_id = :board_id
            RETURNING id, board_id, collection_name, collection_description, collection_configuration, created_at, updated_at;
        """)

        values = {
            "collection_name": quadrant_collection_table.collection_name,
            "collection_description": quadrant_collection_table.collection_description,
            "collection_configuration": quadrant_collection_table.collection_configuration,
            "board_id": board_id
        }

        updated_table_data_tuple = self.execute_query(query, values)
        if updated_table_data_tuple:
            updated_table_instance = QuadrantCollectionTable(**dict(zip(QuadrantCollectionTable.__annotations__, updated_table_data_tuple)))
            return updated_table_instance
        return None  # If update fails, return None
