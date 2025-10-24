# SSMERGE Bot - Professional Telegram Video Merger

## Project Overview
Professional Telegram bot for merging videos with DDL support, dual upload system, and authorization management.

## Architecture
- **bot.py**: Main bot entry point with Pyrogram client
- **config.py**: Environment configuration handler
- **helpers/**: Core functionality modules
  - `database.py`: MongoDB integration
  - `downloader.py`: DDL and direct link downloads with GoFile support
  - `merger.py`: Professional video merging with ffmpeg
  - `uploader.py`: Dual upload (Telegram + GoFile)
  - `utils.py`: Helper functions

## Features
✅ Authorized group-only operation
✅ Private chat intro for unauthorized users
✅ DDL download support with GoFile integration
✅ Dual upload system (Telegram/GoFile)
✅ Professional progress tracking
✅ Task management (Stop/Cancel/Status)
✅ Owner controls

## Setup Requirements
1. Python 3.11+
2. MongoDB database
3. FFmpeg (for video processing)
4. Telegram API credentials

## Environment Variables
Required in `config.env`:
- API_HASH
- BOT_TOKEN
- TELEGRAM_API
- OWNER
- OWNER_USERNAME
- DATABASE_URL

Optional:
- PASSWORD
- GOFILE_TOKEN
- AUTH_GROUPS

## Development Notes
- Bot works ONLY in authorized groups
- Private chats show intro message
- Owner has full access automatically
- All video operations use professional progress bars
- Error handling with retry logic

## Recent Changes
- Implemented authorization system
- Added MongoDB integration
- Created dual upload system
- Enhanced downloader with GoFile support
- Professional merger with container compatibility

## Next Steps
- Add more professional features
- Implement task cancellation
- Add owner dashboard
- Enhance error reporting
