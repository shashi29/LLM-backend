# app/repositories/users_repository.py
class UsersRepository:
    def __init__(self):
        self.users = []  # In-memory list to store users

    def create_user(self, user):
        self.users.append(user.dict())
        return user

    def get_users(self):
        return self.users

    def get_user_by_id(self, user_id):
        return next((u for u in self.users if u["id"] == user_id), None)
