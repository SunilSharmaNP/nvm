#!/usr/bin/env python3
from dotenv import load_dotenv
load_dotenv("config.env", override=True)

import os
import time
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from __init__ import LOGGER, queueDB, active_tasks
from config import config
from helpers.database import Database
from helpers.utils import UserSettings, get_readable_time

botStartTime = time.time()

class MergeBot(Client):
    def __init__(self):
        super().__init__(
            name="merge-bot",
            api_hash=config.API_HASH,
            api_id=config.TELEGRAM_API,
            bot_token=config.BOT_TOKEN,
            workers=50,
            app_version="3.0+pro"
        )
        self.db = Database()
    
    async def start(self):
        await super().start()
        try:
            await self.send_message(
                chat_id=int(config.OWNER),
                text=f"🚀 **Bot Started!**\n\n⏰ {time.strftime('%Y-%m-%d %H:%M:%S')}\n🤖 SSMERGE Bot v3.0"
            )
        except:
            pass
        LOGGER.info("✅ Bot Started Successfully!")
    
    async def stop(self, *args):
        await super().stop()
        LOGGER.info("🛑 Bot Stopped")

mergeApp = MergeBot()

os.makedirs("downloads", exist_ok=True)

async def is_authorized(client, message):
    user_id = message.from_user.id if message.from_user else message.sender_chat.id
    chat_id = message.chat.id
    
    if user_id == int(config.OWNER):
        return True
    
    if message.chat.type == "private":
        user = UserSettings(user_id, message.from_user.first_name if message.from_user else "User")
        return user.allowed
    else:
        return mergeApp.db.is_authorized_group(chat_id)

@mergeApp.on_message(filters.command(["start"]) & filters.private)
async def start_handler(client, message):
    user = UserSettings(message.from_user.id, message.from_user.first_name)
    
    if message.from_user.id != int(config.OWNER) and not user.allowed:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("ℹ️ About", callback_data="about")],
            [InlineKeyboardButton("📞 Owner", url=f"https://t.me/{config.OWNER_USERNAME}")]
        ])
        
        await message.reply_text(
            f"👋 **Hi {message.from_user.first_name}!**\n\n"
            "🤖 **I Am Professional Video Merge Bot**\n\n"
            "⚠️ **This bot works only in authorized groups**\n\n"
            f"📞 Contact: @{config.OWNER_USERNAME}",
            reply_markup=keyboard
        )
        return
    
    if message.from_user.id == int(config.OWNER):
        user.allowed = True
        user.set()
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚙️ Settings", callback_data="settings")],
        [InlineKeyboardButton("ℹ️ About", callback_data="about"),
         InlineKeyboardButton("📊 Stats", callback_data="stats")],
        [InlineKeyboardButton("📞 Owner", url=f"https://t.me/{config.OWNER_USERNAME}")]
    ])
    
    await message.reply_text(
        f"👋 **Hi {message.from_user.first_name}!**\n\n"
        "🤖 **I Am Professional Video Merge Bot**\n\n"
        "✅ You are authorized!\n"
        f"⏱ Uptime: `{get_readable_time(int(time.time() - botStartTime))}`",
        reply_markup=keyboard
    )

@mergeApp.on_message(filters.command(["start"]) & filters.group)
async def group_start_handler(client, message):
    if not await is_authorized(client, message):
        await message.reply_text(
            "⚠️ **This is an authorized group-only bot!**\n\n"
            f"📞 Contact: @{config.OWNER_USERNAME}"
        )
        return
    
    await message.reply_text(
        "🤖 **SSMERGE Bot is Active!**\n\n"
        "✅ This group is authorized\n"
        "📹 You can merge videos here!"
    )

@mergeApp.on_message(filters.command(["authgroup"]) & filters.private)
async def authgroup_handler(client, message):
    if message.from_user.id != int(config.OWNER):
        await message.reply_text("❌ Owner only command!")
        return
    
    try:
        group_id = int(message.text.split()[1])
        mergeApp.db.add_authorized_group(group_id)
        await message.reply_text(f"✅ Group `{group_id}` authorized successfully!")
    except:
        await message.reply_text("Usage: `/authgroup <group_id>`")

@mergeApp.on_message(filters.command(["deauthgroup"]) & filters.private)
async def deauthgroup_handler(client, message):
    if message.from_user.id != int(config.OWNER):
        await message.reply_text("❌ Owner only command!")
        return
    
    try:
        group_id = int(message.text.split()[1])
        mergeApp.db.remove_authorized_group(group_id)
        await message.reply_text(f"✅ Group `{group_id}` deauthorized!")
    except:
        await message.reply_text("Usage: `/deauthgroup <group_id>`")

LOGGER.info("Loading plugins...")
mergeApp.run()
