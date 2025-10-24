import pymongo
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
from config import config
from __init__ import LOGGER

class Database:
    def __init__(self):
        try:
            self.client = MongoClient(config.DATABASE_URL, serverSelectionTimeoutMS=5000)
            self.client.admin.command('ping')
            self.db = self.client['mergebot']
            self.users = self.db['users']
            self.groups = self.db['authorized_groups']
            LOGGER.info("✅ Database connected successfully")
        except ConnectionFailure as e:
            LOGGER.error(f"❌ Database connection failed: {e}")
            raise
        except Exception as e:
            LOGGER.error(f"❌ Database initialization error: {e}")
            raise
    
    def get_user(self, user_id: int):
        try:
            return self.users.find_one({'user_id': user_id})
        except Exception as e:
            LOGGER.error(f"Error fetching user {user_id}: {e}")
            return None
    
    def update_user(self, user_id: int, data: dict):
        try:
            self.users.update_one(
                {'user_id': user_id},
                {'$set': data},
                upsert=True
            )
            return True
        except Exception as e:
            LOGGER.error(f"Error updating user {user_id}: {e}")
            return False
    
    def is_authorized_group(self, group_id: int):
        try:
            return self.groups.find_one({'group_id': group_id}) is not None
        except Exception as e:
            LOGGER.error(f"Error checking group {group_id}: {e}")
            return False
    
    def add_authorized_group(self, group_id: int, group_name: str = ""):
        try:
            self.groups.update_one(
                {'group_id': group_id},
                {'$set': {'group_name': group_name}},
                upsert=True
            )
            return True
        except Exception as e:
            LOGGER.error(f"Error adding group {group_id}: {e}")
            return False
    
    def remove_authorized_group(self, group_id: int):
        try:
            self.groups.delete_one({'group_id': group_id})
            return True
        except Exception as e:
            LOGGER.error(f"Error removing group {group_id}: {e}")
            return False
    
    def get_all_users(self):
        try:
            return list(self.users.find())
        except Exception as e:
            LOGGER.error(f"Error fetching all users: {e}")
            return []
    
    def get_all_groups(self):
        try:
            return list(self.groups.find())
        except Exception as e:
            LOGGER.error(f"Error fetching all groups: {e}")
            return []
