# app/repositories/main_board_repository.py
class MainBoardRepository:
    def __init__(self):
        self.main_boards = []  # In-memory list to simulate a database

    def create_main_board(self, main_board):
        # Simulate assigning a unique ID
        main_board_data = main_board.dict()
        main_board_data["id"] = len(self.main_boards) + 1
        self.main_boards.append(main_board_data)
        return main_board_data

    def get_all_main_boards(self):
        return self.main_boards

    def get_all_info_tree(self):
        # Simulate a hierarchical view of boards
        tree = []
        for main_board in self.main_boards:
            tree.append(
                {
                    "main_board": main_board,
                    "boards": [board for board in BoardsRepository().get_boards() if board["main_board_id"] == main_board["id"]]
                }
            )
        return tree

    def get_main_board(self, main_board_id):
        return next((mb for mb in self.main_boards if mb["id"] == main_board_id), None)

    def update_main_board(self, main_board_id, main_board):
        for index, existing_main_board in enumerate(self.main_boards):
            if existing_main_board["id"] == main_board_id:
                self.main_boards[index] = main_board.dict()
                self.main_boards[index]["id"] = main_board_id
                return self.main_boards[index]
        return None

    def delete_main_board(self, main_board_id):
        for main_board in self.main_boards:
            if main_board["id"] == main_board_id:
                self.main_boards.remove(main_board)
                return main_board
        return None
