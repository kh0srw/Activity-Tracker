# Activity Tracker Telegram Bot

A pure inline-keyboard Telegram bot for monitoring your activity stats remotely.

## Features

- 📊 **Today's Stats** - Active time, break time, total system time
- 📱 **Top Apps** - Application breakdown with percentages
- 📅 **Yesterday** - View previous day's stats
- 📆 **Weekly** - Last 7 days summary
- 🔄 **Refresh** - Update data anytime

**100% Button-Based** - No typing required, just tap!

## Setup

### 1. Create a Telegram Bot

1. Open Telegram and message [@BotFather](https://t.me/BotFather)
2. Send `/newbot` and follow the prompts
3. Copy the bot token (looks like `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 2. Get Your User ID (Optional but Recommended)

1. Message [@userinfobot](https://t.me/userinfobot) on Telegram
2. It will reply with your user ID (a number)
3. Use this to restrict bot access to only you

### 3. Set Environment Variables

Create a `.env` file in the `bot/` folder:

```env
# Required: Your bot token from BotFather
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz

# Optional: Restrict to your user ID only
TELEGRAM_USER_IDS=123456789

# Optional: Custom database path
# DB_PATH=C:/path/to/activity_tracker.db
```

Or set them in your system environment.

### 4. Install Dependencies

```bash
cd bot
pip install -r requirements.txt
```

### 5. Run the Bot

```bash
python bot.py
```

## Usage

1. Start a chat with your bot on Telegram
2. Send `/start` (only needed once)
3. Use the inline buttons to navigate!

## Bot Interface

```
🖥️ Activity Tracker Bot

[📊 Today's Stats]
[📱 Top Apps Today]
[📅 Yesterday] [📆 This Week]
[🔄 Refresh]
```

Each view has a **Back to Menu** button and quick navigation between Stats and Apps.

## Running Alongside Tracker

The bot reads the database in read-only mode and runs completely independently:

```bash
# Terminal 1: Run the watcher
cd watcher
python watcher.py

# Terminal 2: Run the bot
cd bot
python bot.py
```

Both can run simultaneously without conflicts.

