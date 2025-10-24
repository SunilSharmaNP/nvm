import os
import sys
import logging
from collections import defaultdict
from logging.handlers import RotatingFileHandler

MERGE_MODE = {}
UPLOAD_AS_DOC = {}
UPLOAD_TO_DRIVE = {}

FINISHED_PROGRESS_STR = os.environ.get("FINISHED_PROGRESS_STR", "█")
UN_FINISHED_PROGRESS_STR = os.environ.get("UN_FINISHED_PROGRESS_STR", "░")
EDIT_SLEEP_TIME_OUT = 10

gDict = defaultdict(lambda: [])
queueDB = {}
formatDB = {}
replyDB = {}
active_tasks = {}

VIDEO_EXTENSIONS = ["mkv", "mp4", "webm", "ts", "wav", "mov", "avi", "flv", "m4v"]
AUDIO_EXTENSIONS = ["aac", "ac3", "eac3", "m4a", "mka", "thd", "dts", "mp3", "flac", "opus"]
SUBTITLE_EXTENSIONS = ["srt", "ass", "mka", "mks", "vtt"]

os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
    handlers=[
        RotatingFileHandler("logs/mergebot.log", maxBytes=50000000, backupCount=10),
        logging.StreamHandler(sys.stdout),
    ],
)
logging.getLogger("pyrogram").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("PIL").setLevel(logging.WARNING)

LOGGER = logging.getLogger(__name__)
