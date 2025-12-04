# Complete Setup Guide 🚀

## Prerequisites Check

Before starting, ensure you have:
- ✅ Windows 10 or 11
- ✅ Python 3.11 or higher
- ✅ Docker Desktop (optional, for dashboard container)
- ✅ Git (optional)

## Step-by-Step Installation

### Step 1: Get the Code

```bash
# Create project directory
mkdir activity-tracker-pro
cd activity-tracker-pro

# If using Git:
git clone <repo-url> .

# Or download and extract the ZIP file
```

### Step 2: Set Up Python Environment

#### Option A: Using Virtual Environment (Recommended)

```bash
# Create virtual environment
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate
```

#### Option B: Using Global Python

Skip this if you prefer global installation (not recommended for production).

### Step 3: Install Watcher Dependencies

```bash
cd watcher
pip install -r requirements.txt
cd ..
```

### Step 4: Install Dashboard Dependencies (If Running Without Docker)

```bash
cd dashboard
pip install -r requirements.txt
cd ..
```

### Step 5: Configure Environment

```bash
# Copy example environment file
copy .env.example .env

# Edit .env file with your favorite text editor
notepad .env
```

**Important**: Add your Gemini API key if you want AI insights:
```env
GEMINI_API_KEY=your_actual_api_key_here
```

Get your key from: https://makersuite.google.com/app/apikey

### Step 6: Test Watcher (Dry Run)

```bash
cd watcher
python watcher.py
```

You should see:
- ✅ System tray icon appears (green square)
- ✅ Console output: "Activity Watcher STARTED"
- ✅ Database created at `~/ActivityTracker/data/activity.db`

**Test the hotkeys**:
- Press `Ctrl+Alt+Shift+I` → Should hear beep, icon turns red
- Press `Ctrl+Alt+Shift+O` → Should hear beep, icon turns green

**Stop the watcher**: Right-click system tray icon → Exit

### Step 7: Run Dashboard

#### Option A: Using Docker (Recommended)

```bash
# Make sure watcher is running first!
# Then in a new terminal:
docker-compose up dashboard
```

Wait for:
```
dashboard_1  | You can now view your Streamlit app in your browser.
dashboard_1  | URL: http://localhost:8501
```

#### Option B: Native Python

```bash
cd dashboard
streamlit run app.py
```

### Step 8: Verify Everything Works

1. **Open browser**: http://localhost:8501
2. **You should see**: Dashboard with "No activity data" message (normal for first run)
3. **Work for 2 minutes**: Open VSCode, write some code
4. **Refresh dashboard**: Should now show activity!

## Configuration Guide

### Customizing Application Categories

Edit `watcher/config.py`:

```python
# Add your primary coding tools
PRIMARY_WORK_APPS = {
    "code.exe": "VSCode",
    "cursor.exe": "Cursor",
    "pycharm64.exe": "PyCharm",
    "yourapp.exe": "Your App Name",  # Add here!
}

# Add communication tools
SECONDARY_WORK_APPS = {
    "telegram.exe": "Telegram",
    "slack.exe": "Slack",
    "discord.exe": "Discord",
    # Add yours
}
```

### Customizing Work Domains

Still in `watcher/config.py`:

```python
WORK_DOMAINS = [
    "github.com",
    "stackoverflow.com",
    "your-company.com",  # Add your domains!
    "localhost",
    "127.0.0.1",
]
```

### Adjusting Tracking Intervals

```python
# Sample rate (how often to check active window)
SAMPLE_INTERVAL = 1  # 1 second (default)

# Session creation (how often to save to database)
FLUSH_INTERVAL = 30  # 30 seconds (default)

# Auto-idle trigger
IDLE_THRESHOLD = 300  # 5 minutes (default)
```

**Recommendations**:
- **High accuracy**: `SAMPLE_INTERVAL = 1`, `FLUSH_INTERVAL = 30`
- **Lower CPU**: `SAMPLE_INTERVAL = 2`, `FLUSH_INTERVAL = 60`
- **Battery saving**: `SAMPLE_INTERVAL = 5`, `FLUSH_INTERVAL = 120`

## Running in Production

### Watcher: Auto-Start on Windows Boot

The watcher automatically registers itself to start with Windows. To verify:

1. Press `Win + R`
2. Type: `shell:startup`
3. You should see a shortcut to the watcher

To manually create:
```bash
# Create a .bat file in the startup folder
echo python "C:\path\to\watcher.py" > "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\activity-watcher.bat"
```

### Dashboard: Always-On Docker Service

```bash
# Start in detached mode
docker-compose up -d dashboard

# Check status
docker-compose ps

# View logs
docker-compose logs -f dashboard

# Stop
docker-compose down
```

### Background Operation

#### Watcher
- Runs in system tray
- Minimal CPU usage (~0.1%)
- Memory: ~50MB
- No visible windows

#### Dashboard
- Accessible at http://localhost:8501
- Auto-refresh available in UI
- Can run 24/7

## Maintenance

### Backup Your Data

```bash
# Database location
~/ActivityTracker/data/activity.db

# Create backup
copy "%USERPROFILE%\ActivityTracker\data\activity.db" backup_YYYYMMDD.db
```

### View Logs

```bash
# Watcher logs
type "%USERPROFILE%\ActivityTracker\logs\watcher.log"

# Dashboard logs (Docker)
docker-compose logs dashboard

# Dashboard logs (Native)
# Check terminal output
```

### Clear Old Data (Optional)

```sql
-- Open database with any SQLite browser
-- Delete sessions older than 90 days
DELETE FROM sessions WHERE start_time < datetime('now', '-90 days');
DELETE FROM idle_periods WHERE start_time < datetime('now', '-90 days');

-- Vacuum to reclaim space
VACUUM;
```

## Performance Tuning

### For Large Databases (100k+ sessions)

1. **Dashboard loading slow?**
   - Reduce date range in sidebar (use 7-14 days instead of 30)
   - Add indexes (already included, but verify):
     ```sql
     CREATE INDEX IF NOT EXISTS idx_sessions_start ON sessions(start_time);
     CREATE INDEX IF NOT EXISTS idx_sessions_category ON sessions(category);
     ```

2. **Watcher using too much memory?**
   - Increase `FLUSH_INTERVAL` to 60-120 seconds
   - This reduces database write frequency

3. **Dashboard charts rendering slow?**
   - Reduce `MAX_TIMELINE_SESSIONS` in `dashboard/config.py`
   - Default is 50, try 25

## Troubleshooting

### Problem: Watcher won't start

**Solution 1**: Run as Administrator
```bash
# Right-click Command Prompt → Run as Administrator
cd watcher
python watcher.py
```

**Solution 2**: Check Python version
```bash
python --version
# Should be 3.11+
```

**Solution 3**: Reinstall dependencies
```bash
cd watcher
pip install --force-reinstall -r requirements.txt
```

### Problem: Dashboard shows "Database not found"

**Causes**:
1. Watcher hasn't run yet
2. Database path mismatch
3. Permissions issue

**Solutions**:
```bash
# Check if database exists
dir "%USERPROFILE%\ActivityTracker\data"

# Should show: activity.db

# If missing, run watcher for 30 seconds

# If path is different, update .env:
DB_PATH=C:\your\custom\path\activity.db
```

### Problem: No data appearing in dashboard

**Checklist**:
1. ✅ Watcher running? (check system tray)
2. ✅ Green icon? (not red/idle)
3. ✅ Working in tracked apps? (VSCode, browser, etc.)
4. ✅ Waited 30+ seconds?
5. ✅ Refreshed dashboard?

**Debug**:
```bash
# Check watcher logs
type "%USERPROFILE%\ActivityTracker\logs\watcher.log"

# Look for lines like:
# "Session recorded: VSCode | 30s | FG: 28.0s"
```

### Problem: AI insights not working

**Solution**:
1. Get API key: https://makersuite.google.com/app/apikey
2. Add to `.env`: `GEMINI_API_KEY=your_key_here`
3. Restart dashboard
4. Verify: Sidebar should show "AI Assistant: ✅ Ready"

### Problem: Docker dashboard won't start

**Check Docker Desktop**:
```bash
# Is Docker running?
docker --version
docker ps

# Rebuild dashboard
docker-compose build dashboard
docker-compose up dashboard
```

**Port conflict**:
```bash
# If port 8501 is in use, change in docker-compose.yml:
ports:
  - "8502:8501"  # Use 8502 instead
```

## Advanced Usage

### Multiple Machines

Track activity on multiple computers:

1. **Separate databases per machine** (default)
   - Each machine has its own `~/ActivityTracker/data/activity.db`

2. **Centralized database** (advanced)
   - Set up network share
   - Point all machines to same database:
     ```env
     DB_PATH=\\network-share\ActivityTracker\activity.db
     ```

### Team Analytics (Future Feature)

Currently single-user. For teams:
- Run watcher on each team member's machine
- Aggregate databases server-side
- Host dashboard on shared server

(Implementation guide coming soon)

### Export Data

```python
# Simple Python script to export to CSV
import sqlite3
import pandas as pd

conn = sqlite3.connect('path/to/activity.db')
df = pd.read_sql_query("SELECT * FROM sessions", conn)
df.to_csv('export.csv', index=False)
conn.close()
```

## Security Best Practices

1. **Database encryption** (optional):
   - Use SQLCipher instead of SQLite
   - Requires code modifications

2. **API key security**:
   - Never commit `.env` to Git
   - Use environment variables in production

3. **Network security**:
   - Dashboard runs on localhost by default
   - To expose: use reverse proxy (nginx/Caddy) with SSL

## Getting Help

1. **Check logs first**:
   - Watcher: `~/ActivityTracker/logs/watcher.log`
   - Dashboard: Terminal output or Docker logs

2. **Common issues**: See Troubleshooting section above

3. **GitHub Issues**: Open detailed bug report with:
   - OS version
   - Python version
   - Error logs
   - Steps to reproduce

4. **Community**: GitHub Discussions for questions

## Next Steps

1. ✅ Let it run for a day
2. ✅ Check your productivity scores
3. ✅ Generate AI insights
4. ✅ Customize categories for your workflow
5. ✅ Share feedback!

---

**Happy tracking! 📊✨**