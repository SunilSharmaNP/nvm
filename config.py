import os
import sys
from typing import Optional

class ConfigError(Exception):
    pass

class Config:
    @staticmethod
    def get_env(var: str, required: bool = True, default: Optional[str] = None) -> Optional[str]:
        value = os.environ.get(var, default)
        if required and not value:
            raise ConfigError(f"❌ Required: '{var}' not set!")
        return value

def _load_config():
    API_HASH = Config.get_env("API_HASH")
    BOT_TOKEN = Config.get_env("BOT_TOKEN")
    TELEGRAM_API = int(Config.get_env("TELEGRAM_API"))
    OWNER = int(Config.get_env("OWNER"))
    OWNER_USERNAME = Config.get_env("OWNER_USERNAME")
    DATABASE_URL = Config.get_env("DATABASE_URL")
    
    PASSWORD = Config.get_env("PASSWORD", False, "mergebot123")
    LOGCHANNEL = Config.get_env("LOGCHANNEL", False)
    GDRIVE_FOLDER_ID = Config.get_env("GDRIVE_FOLDER_ID", False, "root")
    USER_SESSION_STRING = Config.get_env("USER_SESSION_STRING", False)
    GOFILE_TOKEN = Config.get_env("GOFILE_TOKEN", False)
    
    AUTH_GROUPS = Config.get_env("AUTH_GROUPS", False, "")
    
    MAX_CONCURRENT_USERS = int(Config.get_env("MAX_CONCURRENT_USERS", False, "5"))
    MAX_FILE_SIZE = int(Config.get_env("MAX_FILE_SIZE", False, "2147483648"))
    
    Config.API_HASH = API_HASH
    Config.BOT_TOKEN = BOT_TOKEN
    Config.TELEGRAM_API = TELEGRAM_API
    Config.OWNER = OWNER
    Config.OWNER_USERNAME = OWNER_USERNAME
    Config.DATABASE_URL = DATABASE_URL
    Config.PASSWORD = PASSWORD
    Config.LOGCHANNEL = LOGCHANNEL
    Config.GDRIVE_FOLDER_ID = GDRIVE_FOLDER_ID
    Config.USER_SESSION_STRING = USER_SESSION_STRING
    Config.GOFILE_TOKEN = GOFILE_TOKEN
    Config.AUTH_GROUPS = AUTH_GROUPS
    Config.MAX_CONCURRENT_USERS = MAX_CONCURRENT_USERS
    Config.MAX_FILE_SIZE = MAX_FILE_SIZE
    Config.IS_PREMIUM = False
    Config.MODES = ["video-video", "video-audio", "video-subtitle", "extract-streams"]

try:
    _load_config()
except:
    pass

config = Config()
