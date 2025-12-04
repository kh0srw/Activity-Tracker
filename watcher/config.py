"""
Configuration for Activity Tracker - Simple Raw Mode
No filtering, no categorization - tracks everything
"""

import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"

# Create directories
DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

# Database
DB_PATH = DATA_DIR / "activity_tracker.db"

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Tracking Settings
POLL_INTERVAL = 0.5  # Poll every 500ms for responsive tracking
MIN_ACTIVITY_DURATION = 1  # Minimum 1 second to record (filter noise)

# Hotkey (Ctrl+Alt+Shift+P)
HOTKEY_TOGGLE = "ctrl+alt+shift+p"

# System Tray Icon Colors
ICON_COLOR_ACTIVE = "#10B981"   # Green - tracking
ICON_COLOR_PAUSED = "#F59E0B"   # Orange - paused
