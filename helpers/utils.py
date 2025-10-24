import os
import time
import asyncio
import json
from typing import Optional
from helpers.database import Database
from __init__ import LOGGER

SIZE_UNITS = ["B", "KB", "MB", "GB", "TB", "PB"]

def get_readable_file_size(size_in_bytes):
    if size_in_bytes is None:
        return "0B"
    index = 0
    while size_in_bytes >= 1024 and index < len(SIZE_UNITS) - 1:
        size_in_bytes /= 1024
        index += 1
    return f"{size_in_bytes:.2f}{SIZE_UNITS[index]}" if index > 0 else f"{size_in_bytes:.0f}B"

def get_readable_time(seconds: int) -> str:
    periods = [('d', 86400), ('h', 3600), ('m', 60), ('s', 1)]
    result = []
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            result.append(f'{int(period_value)}{period_name}')
    return ' '.join(result) if result else '0s'

def get_human_readable_size(size_bytes):
    return get_readable_file_size(size_bytes)

def get_progress_bar(progress: float, length: int = 20) -> str:
    filled_len = int(length * progress)
    return "█" * filled_len + "░" * (length - filled_len)

async def get_video_properties(file_path: str):
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_format', '-show_streams', file_path
        ]
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await process.communicate()
        
        if process.returncode != 0:
            return None
        
        metadata = json.loads(stdout.decode())
        video_stream = next((s for s in metadata.get('streams', []) if s.get('codec_type') == 'video'), None)
        
        return {
            'duration': int(float(metadata.get('format', {}).get('duration', 0))),
            'width': video_stream.get('width', 0) if video_stream else 0,
            'height': video_stream.get('height', 0) if video_stream else 0,
            'size': int(metadata.get('format', {}).get('size', 0))
        }
    except Exception as e:
        LOGGER.error(f"Error getting video properties: {e}")
        return None

class UserSettings:
    def __init__(self, user_id: int, user_name: str):
        self.user_id = user_id
        self.user_name = user_name
        self.db = Database()
        self._load_settings()
    
    def _load_settings(self):
        user_data = self.db.get_user(self.user_id)
        if user_data:
            self.allowed = user_data.get('allowed', False)
            self.banned = user_data.get('banned', False)
            self.merge_mode = user_data.get('merge_mode', 1)
            self.upload_as_doc = user_data.get('upload_as_doc', False)
            self.upload_to_drive = user_data.get('upload_to_drive', False)
        else:
            self.allowed = False
            self.banned = False
            self.merge_mode = 1
            self.upload_as_doc = False
            self.upload_to_drive = False
    
    def set(self):
        self.db.update_user(
            self.user_id,
            {
                'user_name': self.user_name,
                'allowed': self.allowed,
                'banned': self.banned,
                'merge_mode': self.merge_mode,
                'upload_as_doc': self.upload_as_doc,
                'upload_to_drive': self.upload_to_drive,
                'last_activity': int(time.time())
            }
        )
        LOGGER.info(f"User settings saved: {self.user_id} - Allowed: {self.allowed}")
