"""
Telegram Bot Configuration
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Token (get from @BotFather)
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7691772842:AAFLRGFSNwi8JDsSQq91t9Rs9zSezgMSpOk")

# Your Telegram User ID (for security - only you can use the bot)
# Get it from @userinfobot on Telegram
ALLOWED_USER_IDS = [
    int(uid.strip()) 
    for uid in os.getenv("TELEGRAM_USER_IDS", "1359086536").split(",") 
    if uid.strip()
]

# Database path - same as watcher
DB_PATH = os.getenv(
    "DB_PATH",
    str(Path(__file__).parent.parent / "watcher" / "data" / "activity_tracker.db")
)

# Bot settings
REFRESH_COOLDOWN = 5  # seconds between refreshes
MAX_APPS_DISPLAY = 10  # max apps to show in breakdown

