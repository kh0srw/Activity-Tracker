"""
Dashboard Configuration - Simplified
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Database
# Default to the watcher's database location
DB_PATH = os.getenv(
    "DB_PATH", 
    str(Path(__file__).parent.parent / "watcher" / "data" / "activity_tracker.db")
)

# Dashboard Settings
PAGE_TITLE = "Activity Tracker"
PAGE_ICON = "📊"
LAYOUT = "wide"

# Data Settings
DEFAULT_DATE_RANGE = 7  # days

# Colors
COLOR_ACTIVE = "#10B981"   # Green - active time
COLOR_BREAK = "#F59E0B"    # Orange - break time

# Chart Settings
CHART_HEIGHT = 400
