# app/repositories/boards_repository.py
class BoardsRepository:
    def __init__(self):
        self.boards = []  # In-memory list to simulate a database

    def create_board(self, board):
        # Simulate assigning a unique ID
        board_data = board.dict()
        board_data["id"] = len(self.boards) + 1
        self.boards.append(board_data)
        return board_data

    def get_boards(self):
        return self.boards

    def get_board(self, board_id):
        return next((board for board in self.boards if board["id"] == board_id), None)

    def update_board(self, board_id, board):
        for index, existing_board in enumerate(self.boards):
            if existing_board["id"] == board_id:
                self.boards[index] = board.dict()
                self.boards[index]["id"] = board_id
                return self.boards[index]
        return None

    def delete_board(self, board_id):
        for board in self.boards:
            if board["id"] == board_id:
                self.boards.remove(board)
                return board
        return None

    def get_boards_for_main_boards(self, main_board_id):
        return [board for board in self.boards if board["main_board_id"] == main_board_id]
