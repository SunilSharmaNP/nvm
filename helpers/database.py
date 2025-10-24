import pymongo
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
from config import config
from __init__ import LOGGER

class Database:
    def __init__(self):
        self.client = None
        self.db = None
        self.users = None
        self.groups = None
        self.connected = False
        
        try:
            self.client = MongoClient(config.DATABASE_URL, serverSelectionTimeoutMS=5000)
            self.client.admin.command('ping')
            self.db = self.client['mergebot']
            self.users = self.db['users']
            self.groups = self.db['authorized_groups']
            self.connected = True
            LOGGER.info("✅ Database connected successfully")
        except (ConnectionFailure, OperationFailure) as e:
            LOGGER.warning(f"⚠️ Database connection failed: {e}")
            LOGGER.warning("⚠️ Bot will run in limited mode without database")
        except Exception as e:
            LOGGER.warning(f"⚠️ Database initialization error: {e}")
            LOGGER.warning("⚠️ Bot will run in limited mode without database")
    
    def get_user(self, user_id: int):
        if not self.connected:
            return None
        try:
            return self.users.find_one({'user_id': user_id})
        except Exception as e:
            LOGGER.error(f"Error fetching user {user_id}: {e}")
            return None
    
    def update_user(self, user_id: int, data: dict):
        if not self.connected:
            return False
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
        if not self.connected:
            return False
        try:
            return self.groups.find_one({'group_id': group_id}) is not None
        except Exception as e:
            LOGGER.error(f"Error checking group {group_id}: {e}")
            return False
    
    def add_authorized_group(self, group_id: int, group_name: str = ""):
        if not self.connected:
            return False
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
        if not self.connected:
            return False
        try:
            self.groups.delete_one({'group_id': group_id})
            return True
        except Exception as e:
            LOGGER.error(f"Error removing group {group_id}: {e}")
            return False
    
    def get_all_users(self):
        if not self.connected:
            return []
        try:
            return list(self.users.find())
        except Exception as e:
            LOGGER.error(f"Error fetching all users: {e}")
            return []
    
    def get_all_groups(self):
        if not self.connected:
            return []
        try:
            return list(self.groups.find())
        except Exception as e:
            LOGGER.error(f"Error fetching all groups: {e}")
            return []
