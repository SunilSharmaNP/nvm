# SSMERGE - Professional Telegram Video Merger Bot

A professional Telegram bot for merging videos with advanced features like DDL support, dual upload (Telegram/GoFile), and task management.

## Features

✅ Merge multiple videos
✅ Direct Download Link (DDL) support
✅ Dual upload system (Telegram & GoFile)
✅ Authorized group management
✅ Professional progress tracking
✅ Task management (Stop/Cancel/Status)
✅ Owner controls
✅ Database-backed user management

## Setup

1. Copy `config.env.sample` to `config.env`
2. Fill in your configuration values
3. Install dependencies: `pip install -r requirements.txt`
4. Run: `python bot.py`

## Commands

- `/start` - Start the bot
- `/authgroup <group_id>` - Authorize a group (Owner only)
- `/deauthgroup <group_id>` - Deauthorize a group (Owner only)

## Requirements

- Python 3.11+
- MongoDB database
- FFmpeg installed
- Telegram API credentials

## License

GPL-3.0
