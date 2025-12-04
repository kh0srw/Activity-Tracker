"""
Activity Tracker Telegram Bot
Pure inline keyboard interface - Direct API calls with proxy support
"""

import asyncio
import sqlite3
import json
from datetime import datetime, timedelta
import httpx
import logging

import config

# Proxy configuration for Iran
PROXY_URL = "http://127.0.0.1:10808"

# Telegram Bot API base URL
API_BASE = f"https://api.telegram.org/bot{config.BOT_TOKEN}"

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# ============================================================================
# TELEGRAM API HELPERS
# ============================================================================

async def api_request(method: str, data: dict = None) -> dict:
    """Make a request to Telegram Bot API through proxy"""
    url = f"{API_BASE}/{method}"
    
    async with httpx.AsyncClient(proxy=PROXY_URL, timeout=30.0) as client:
        try:
            if data:
                response = await client.post(url, json=data)
            else:
                response = await client.get(url)
            
            result = response.json()
            
            if not result.get("ok"):
                logger.error(f"API error: {result}")
            
            return result
            
        except Exception as e:
            logger.error(f"Request error: {e}")
            return {"ok": False, "error": str(e)}


async def send_message(chat_id: int, text: str, reply_markup: dict = None) -> dict:
    """Send a message"""
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    if reply_markup:
        data["reply_markup"] = reply_markup
    
    return await api_request("sendMessage", data)


async def edit_message(chat_id: int, message_id: int, text: str, reply_markup: dict = None) -> dict:
    """Edit an existing message"""
    data = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    if reply_markup:
        data["reply_markup"] = reply_markup
    
    return await api_request("editMessageText", data)


async def answer_callback(callback_id: str, text: str = None, show_alert: bool = False) -> dict:
    """Answer a callback query"""
    data = {"callback_query_id": callback_id}
    if text:
        data["text"] = text
        data["show_alert"] = show_alert
    
    return await api_request("answerCallbackQuery", data)


async def get_updates(offset: int = None, timeout: int = 30) -> dict:
    """Get updates using long polling"""
    data = {"timeout": timeout, "allowed_updates": ["message", "callback_query"]}
    if offset:
        data["offset"] = offset
    
    return await api_request("getUpdates", data)


# ============================================================================
# DATABASE QUERIES
# ============================================================================

def get_db_connection():
    """Get database connection"""
    return sqlite3.connect(config.DB_PATH, timeout=10)


def format_duration(minutes: float) -> str:
    """Format minutes to human readable string"""
    if minutes < 1:
        return f"{minutes * 60:.0f}s"
    if minutes < 60:
        return f"{minutes:.0f}m"
    hours = minutes // 60
    mins = minutes % 60
    if mins > 0:
        return f"{hours:.0f}h {mins:.0f}m"
    return f"{hours:.0f}h"


def get_stats_for_date(target_date) -> dict:
    """Get activity stats for a specific date"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        date_str = target_date.isoformat()
        next_date_str = (target_date + timedelta(days=1)).isoformat()
        
        # Active time
        c.execute("""
            SELECT COALESCE(SUM(duration_seconds), 0)
            FROM activity_log
            WHERE timestamp >= ? AND timestamp < ?
        """, (date_str, next_date_str))
        active_seconds = c.fetchone()[0]
        
        # Break time
        c.execute("""
            SELECT COALESCE(SUM(duration_seconds), 0)
            FROM breaks
            WHERE start_time >= ? AND start_time < ?
        """, (date_str, next_date_str))
        break_seconds = c.fetchone()[0]
        
        # Unique apps
        c.execute("""
            SELECT COUNT(DISTINCT process_name)
            FROM activity_log
            WHERE timestamp >= ? AND timestamp < ?
        """, (date_str, next_date_str))
        unique_apps = c.fetchone()[0]
        
        # Activity count
        c.execute("""
            SELECT COUNT(*)
            FROM activity_log
            WHERE timestamp >= ? AND timestamp < ?
        """, (date_str, next_date_str))
        activity_count = c.fetchone()[0]
        
        conn.close()
        
        return {
            'date': target_date,
            'active_min': active_seconds / 60,
            'break_min': break_seconds / 60,
            'system_min': (active_seconds + break_seconds) / 60,
            'unique_apps': unique_apps,
            'activity_count': activity_count,
        }
        
    except Exception as e:
        logger.error(f"Database error: {e}")
        return None


def get_stats_for_range(days: int) -> dict:
    """Get activity stats for last N days"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        start_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        # Active time
        c.execute("""
            SELECT COALESCE(SUM(duration_seconds), 0)
            FROM activity_log
            WHERE timestamp >= ?
        """, (start_date,))
        active_seconds = c.fetchone()[0]
        
        # Break time
        c.execute("""
            SELECT COALESCE(SUM(duration_seconds), 0)
            FROM breaks
            WHERE start_time >= ?
        """, (start_date,))
        break_seconds = c.fetchone()[0]
        
        # Unique apps
        c.execute("""
            SELECT COUNT(DISTINCT process_name)
            FROM activity_log
            WHERE timestamp >= ?
        """, (start_date,))
        unique_apps = c.fetchone()[0]
        
        # Days with activity
        c.execute("""
            SELECT COUNT(DISTINCT DATE(timestamp))
            FROM activity_log
            WHERE timestamp >= ?
        """, (start_date,))
        active_days = c.fetchone()[0]
        
        conn.close()
        
        return {
            'days': days,
            'active_min': active_seconds / 60,
            'break_min': break_seconds / 60,
            'system_min': (active_seconds + break_seconds) / 60,
            'unique_apps': unique_apps,
            'active_days': active_days,
        }
        
    except Exception as e:
        logger.error(f"Database error: {e}")
        return None


def get_top_apps(target_date=None, days: int = None, limit: int = 10) -> list:
    """Get top apps by time"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        if target_date:
            date_str = target_date.isoformat()
            next_date_str = (target_date + timedelta(days=1)).isoformat()
            c.execute("""
                SELECT 
                    REPLACE(process_name, '.exe', '') as app,
                    SUM(duration_seconds) as total_seconds
                FROM activity_log
                WHERE timestamp >= ? AND timestamp < ?
                GROUP BY process_name
                ORDER BY total_seconds DESC
                LIMIT ?
            """, (date_str, next_date_str, limit))
        else:
            start_date = (datetime.now() - timedelta(days=days or 7)).isoformat()
            c.execute("""
                SELECT 
                    REPLACE(process_name, '.exe', '') as app,
                    SUM(duration_seconds) as total_seconds
                FROM activity_log
                WHERE timestamp >= ?
                GROUP BY process_name
                ORDER BY total_seconds DESC
                LIMIT ?
            """, (start_date, limit))
        
        results = c.fetchall()
        conn.close()
        
        # Calculate total for percentages
        total_seconds = sum(r[1] for r in results)
        
        apps = []
        for app_name, seconds in results:
            pct = (seconds / total_seconds * 100) if total_seconds > 0 else 0
            apps.append({
                'name': app_name,
                'minutes': seconds / 60,
                'percentage': pct
            })
        
        return apps
        
    except Exception as e:
        logger.error(f"Database error: {e}")
        return []


# ============================================================================
# KEYBOARDS (as dicts for API)
# ============================================================================

def main_menu_keyboard() -> dict:
    """Main menu inline keyboard"""
    return {
        "inline_keyboard": [
            [{"text": "📊 Today's Stats", "callback_data": "stats_today"}],
            [{"text": "📱 Top Apps Today", "callback_data": "apps_today"}],
            [
                {"text": "📅 Yesterday", "callback_data": "stats_yesterday"},
                {"text": "📆 This Week", "callback_data": "stats_week"}
            ],
            [{"text": "🔄 Refresh", "callback_data": "refresh"}],
        ]
    }


def stats_keyboard(current_view: str) -> dict:
    """Stats view with navigation"""
    period = current_view.split('_')[1]
    return {
        "inline_keyboard": [
            [{"text": "📱 See Top Apps", "callback_data": f"apps_{period}"}],
            [{"text": "◀️ Back to Menu", "callback_data": "menu"}],
        ]
    }


def apps_keyboard(current_view: str) -> dict:
    """Apps view with navigation"""
    period = current_view.split('_')[1]
    return {
        "inline_keyboard": [
            [{"text": "📊 See Stats", "callback_data": f"stats_{period}"}],
            [{"text": "◀️ Back to Menu", "callback_data": "menu"}],
        ]
    }


# ============================================================================
# MESSAGE FORMATTERS
# ============================================================================

def format_welcome_message() -> str:
    """Format welcome message"""
    now = datetime.now().strftime("%H:%M")
    return f"""
🖥️ *Activity Tracker Bot*

📍 Current Time: `{now}`

Select an option below to view your activity stats.
All data is pulled directly from your tracker database.

_Tap any button to get started!_
"""


def format_stats_message(stats: dict, title: str) -> str:
    """Format stats message"""
    if not stats:
        return "❌ *Error*\n\nCould not fetch stats. Is the database accessible?"
    
    active = format_duration(stats['active_min'])
    breaks = format_duration(stats['break_min'])
    total = format_duration(stats['system_min'])
    
    # Progress bar for active ratio
    if stats['system_min'] > 0:
        ratio = stats['active_min'] / stats['system_min']
        filled = int(ratio * 10)
        bar = "█" * filled + "░" * (10 - filled)
        pct = f"{ratio * 100:.0f}%"
    else:
        bar = "░" * 10
        pct = "0%"
    
    msg = f"""
📊 *{title}*
{'─' * 24}

🖥️ *Active Time:* `{active}`
☕ *Break Time:* `{breaks}`
📈 *Total System:* `{total}`

*Active Ratio:* {pct}
`[{bar}]`

📱 *Apps Used:* {stats['unique_apps']}
"""
    
    if 'activity_count' in stats:
        msg += f"🔄 *Window Switches:* {stats['activity_count']}\n"
    
    if 'active_days' in stats:
        msg += f"📅 *Active Days:* {stats['active_days']}/{stats['days']}\n"
    
    timestamp = datetime.now().strftime("%H:%M:%S")
    msg += f"\n_Last updated: {timestamp}_"
    
    return msg


def format_apps_message(apps: list, title: str) -> str:
    """Format top apps message"""
    if not apps:
        return "❌ *Error*\n\nNo app data found for this period."
    
    msg = f"""
📱 *{title}*
{'─' * 24}

"""
    
    # Medal emojis for top 3
    medals = ["🥇", "🥈", "🥉"]
    
    for i, app in enumerate(apps):
        prefix = medals[i] if i < 3 else f"`{i+1}.`"
        duration = format_duration(app['minutes'])
        pct = f"{app['percentage']:.1f}%"
        
        # Mini progress bar
        filled = int(app['percentage'] / 10)
        bar = "▓" * filled + "░" * (10 - filled)
        
        msg += f"{prefix} *{app['name']}*\n"
        msg += f"    `{bar}` {duration} ({pct})\n\n"
    
    timestamp = datetime.now().strftime("%H:%M:%S")
    msg += f"_Last updated: {timestamp}_"
    
    return msg


# ============================================================================
# HANDLERS
# ============================================================================

def check_user(user_id: int) -> bool:
    """Check if user is allowed"""
    if not config.ALLOWED_USER_IDS:
        return True
    return user_id in config.ALLOWED_USER_IDS


async def handle_message(message: dict):
    """Handle incoming message"""
    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]
    text = message.get("text", "")
    
    if not check_user(user_id):
        await send_message(chat_id, "⛔ Unauthorized")
        return
    
    # Any message shows the main menu
    if text.startswith("/start") or text:
        await send_message(
            chat_id,
            format_welcome_message(),
            main_menu_keyboard()
        )


async def handle_callback(callback: dict):
    """Handle callback query from inline keyboard"""
    callback_id = callback["id"]
    user_id = callback["from"]["id"]
    chat_id = callback["message"]["chat"]["id"]
    message_id = callback["message"]["message_id"]
    data = callback.get("data", "")
    
    if not check_user(user_id):
        await answer_callback(callback_id, "⛔ Unauthorized", show_alert=True)
        return
    
    # Acknowledge callback
    await answer_callback(callback_id)
    
    # Main menu
    if data == "menu" or data == "refresh":
        await edit_message(
            chat_id,
            message_id,
            format_welcome_message(),
            main_menu_keyboard()
        )
        return
    
    # Stats views
    if data.startswith("stats_"):
        period = data.split("_")[1]
        
        if period == "today":
            stats = get_stats_for_date(datetime.now().date())
            title = f"Today's Activity ({datetime.now().strftime('%b %d')})"
        elif period == "yesterday":
            yesterday = datetime.now().date() - timedelta(days=1)
            stats = get_stats_for_date(yesterday)
            title = f"Yesterday ({yesterday.strftime('%b %d')})"
        elif period == "week":
            stats = get_stats_for_range(7)
            title = "Last 7 Days"
        else:
            stats = get_stats_for_date(datetime.now().date())
            title = "Stats"
        
        await edit_message(
            chat_id,
            message_id,
            format_stats_message(stats, title),
            stats_keyboard(data)
        )
        return
    
    # Apps views
    if data.startswith("apps_"):
        period = data.split("_")[1]
        
        if period == "today":
            apps = get_top_apps(target_date=datetime.now().date(), limit=config.MAX_APPS_DISPLAY)
            title = f"Top Apps Today ({datetime.now().strftime('%b %d')})"
        elif period == "yesterday":
            yesterday = datetime.now().date() - timedelta(days=1)
            apps = get_top_apps(target_date=yesterday, limit=config.MAX_APPS_DISPLAY)
            title = f"Top Apps Yesterday ({yesterday.strftime('%b %d')})"
        elif period == "week":
            apps = get_top_apps(days=7, limit=config.MAX_APPS_DISPLAY)
            title = "Top Apps (Last 7 Days)"
        else:
            apps = get_top_apps(target_date=datetime.now().date(), limit=config.MAX_APPS_DISPLAY)
            title = "Top Apps"
        
        await edit_message(
            chat_id,
            message_id,
            format_apps_message(apps, title),
            apps_keyboard(data)
        )
        return


# ============================================================================
# MAIN POLLING LOOP
# ============================================================================

async def main():
    """Main bot loop with long polling"""
    if not config.BOT_TOKEN:
        print("❌ Error: BOT_TOKEN not set in config!")
        return
    
    print("=" * 50)
    print("🤖 Activity Tracker Bot Starting...")
    print(f"📁 Database: {config.DB_PATH}")
    print(f"🌐 Proxy: {PROXY_URL}")
    if config.ALLOWED_USER_IDS:
        print(f"🔒 Restricted to user IDs: {config.ALLOWED_USER_IDS}")
    else:
        print("⚠️  No user restrictions (anyone can use)")
    print("=" * 50)
    
    # Test connection
    print("\n🔄 Testing connection to Telegram...")
    me = await api_request("getMe")
    if me.get("ok"):
        bot_name = me["result"]["username"]
        print(f"✅ Connected as @{bot_name}")
    else:
        print(f"❌ Connection failed: {me}")
        return
    
    print("\n✅ Bot is running! Press Ctrl+C to stop.\n")
    
    offset = None
    
    while True:
        try:
            updates = await get_updates(offset=offset, timeout=30)
            
            if not updates.get("ok"):
                logger.error(f"Failed to get updates: {updates}")
                await asyncio.sleep(5)
                continue
            
            for update in updates.get("result", []):
                offset = update["update_id"] + 1
                
                if "message" in update:
                    await handle_message(update["message"])
                
                elif "callback_query" in update:
                    await handle_callback(update["callback_query"])
                    
        except asyncio.CancelledError:
            print("\n👋 Bot stopped.")
            break
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            await asyncio.sleep(5)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user.")
