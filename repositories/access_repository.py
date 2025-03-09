class AccessRepository:
    def __init__(self, roles_repo, users_repo):
        self.roles_repo = roles_repo
        self.users_repo = users_repo

    def get_boards_for_user(self, user_id):
        roles = self.users_repo.get_roles_for_user(user_id)
        boards = []
        for role_id in roles:
            boards.extend(self.roles_repo.get_boards_for_role(role_id))
        return boards

    def validate_access(self, user_id, board_id):
        boards = self.get_boards_for_user(user_id)
        return board_id in boards
