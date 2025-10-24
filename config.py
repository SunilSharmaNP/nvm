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

    API_HASH = get_env.__func__("API_HASH")
    BOT_TOKEN = get_env.__func__("BOT_TOKEN")
    TELEGRAM_API = int(get_env.__func__("TELEGRAM_API"))
    OWNER = int(get_env.__func__("OWNER"))
    OWNER_USERNAME = get_env.__func__("OWNER_USERNAME")
    DATABASE_URL = get_env.__func__("DATABASE_URL")
    
    PASSWORD = get_env.__func__("PASSWORD", False, "mergebot123")
    LOGCHANNEL = get_env.__func__("LOGCHANNEL", False)
    GDRIVE_FOLDER_ID = get_env.__func__("GDRIVE_FOLDER_ID", False, "root")
    USER_SESSION_STRING = get_env.__func__("USER_SESSION_STRING", False)
    GOFILE_TOKEN = get_env.__func__("GOFILE_TOKEN", False)
    
    AUTH_GROUPS = get_env.__func__("AUTH_GROUPS", False, "")
    
    MAX_CONCURRENT_USERS = int(get_env.__func__("MAX_CONCURRENT_USERS", False, "5"))
    MAX_FILE_SIZE = int(get_env.__func__("MAX_FILE_SIZE", False, "2147483648"))
    
    IS_PREMIUM = False
    MODES = ["video-video", "video-audio", "video-subtitle", "extract-streams"]

config = Config()
