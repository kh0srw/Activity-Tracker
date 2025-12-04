# Activity Tracker Pro

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat&logo=Streamlit&logoColor=white)](https://streamlit.io/)

**Activity Tracker Pro** is a production-grade activity tracking system designed for productivity enthusiasts. It features intelligent categorization, Docker deployment, and AI-powered insights to help you track smart, work smarter, and live better.

---

## Table of Contents

- [Features](#-features)
  - [Intelligent Tracking](#intelligent-tracking)
  - [Advanced Analytics](#advanced-analytics)
  - [Production Ready](#production-ready)
  - [AI Insights](#ai-insights)
- [Architecture](#-architecture)
- [Quick Start](#-quick-start)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
- [Usage](#-usage)
  - [Keyboard Shortcuts](#keyboard-shortcuts)
  - [System Tray Icon](#system-tray-icon)
  - [Dashboard Features](#dashboard-features)
- [Configuration](#-configuration)
  - [Watcher Configuration](#watcher-configuration-watcherconfigpy)
  - [Dashboard Configuration](#dashboard-configuration-dashboardconfigpy)
- [Database Schema](#-database-schema)
- [Docker Notes](#-docker-notes)
- [Productivity Metrics Explained](#-productivity-metrics-explained)
- [Privacy & Security](#-privacy--security)
- [Troubleshooting](#-troubleshooting)
- [Roadmap](#-roadmap)
- [Contributing](#-contributing)
- [License](#-license)
- [Acknowledgments](#-acknowledgments)
- [Support](#-support)

---

## Features

### Intelligent Tracking
- **Smart Categorization**: Automatically distinguishes between:
  - **Primary Work**: VSCode, Cursor, IDEs (highest priority)
  - **Secondary Work**: Telegram, Slack, Spotify (supportive tools)
  - **Browser Intelligence**: Detects work vs. leisure domains
  - **Auto-Idle Detection**: No activity for 5 minutes = automatic idle

### Advanced Analytics
- **Deep Work Sessions**: Tracks focused work periods (10+ min, 80%+ active)
- **Productivity Scores**: Focus, Efficiency, Time ROI metrics
- **Activity Heatmaps**: Hour-by-hour, day-by-day patterns
- **Timeline Views**: Visual session history
- **Streak Tracking**: Consecutive productive days

### Production Ready
- **Dockerized Architecture**: Container-based deployment
- **Persistent Storage**: Database survives restarts
- **Health Checks**: Automatic service monitoring
- **Optimized Performance**: Handles months of data efficiently

### AI Insights
- **Gemini Integration**: AI-powered productivity analysis
- **Actionable Recommendations**: Data-driven improvement suggestions
- **Trend Analysis**: Pattern recognition and forecasting

[Back to Top](#-table-of-contents)

---

## Architecture

The system is built with a modular architecture ensuring reliability and scalability:

```
activity-tracker-pro/
├── watcher/          # Background monitoring service (Windows Native)
├── dashboard/        # Streamlit analytics interface (Dockerized)
├── shared/           # Database initialization
└── data/             # Persistent SQLite storage
```

[Back to Top](#-table-of-contents)

---

## Quick Start

### Prerequisites
- **Windows 10/11** (Required for Watcher - needs GUI access)
- **Docker Desktop** (Recommended for Dashboard)
- **Python 3.11+** (For local Watcher execution)

### Installation

1.  **Clone the repository**
    ```bash
    git clone https://github.com/aliasghar5642/Activity-Tracker.git
    cd Activity-Tracker
    ```

2.  **Configure environment**
    ```bash
    cp .env.example .env
    # Edit .env and add your GEMINI_API_KEY (optional)
    ```

3.  **Start the system**

    #### Option A: Windows Native Watcher + Docker Dashboard (Recommended)

    **Terminal 1: Run Watcher on Windows**
    ```bash
    cd watcher
    pip install -r requirements.txt
    python watcher.py
    ```

    **Terminal 2: Run Dashboard in Docker**
    ```bash
    docker-compose up dashboard
    ```

    #### Option B: Everything on Windows (No Docker)

    **Terminal 1: Watcher**
    ```bash
    cd watcher
    pip install -r requirements.txt
    python watcher.py
    ```

    **Terminal 2: Dashboard**
    ```bash
    cd dashboard
    pip install -r requirements.txt
    streamlit run app.py
    ```

4.  **Access Dashboard**
    Open your browser and navigate to: [http://localhost:8501](http://localhost:8501)

[Back to Top](#-table-of-contents)

---

## Usage

### Keyboard Shortcuts
| Shortcut | Action |
|----------|--------|
| `Ctrl+Alt+Shift+I` | Start manual idle mode |
| `Ctrl+Alt+Shift+O` | End idle mode |
| `Ctrl+Alt+Shift+P` | Pause/Resume tracking |

### System Tray Icon
- 🟢 **Green**: Actively tracking
- 🔴 **Red**: Idle mode
- ⚪ **Gray**: Paused

### Dashboard Features
1.  **Time Period Selector**: View last 1-90 days
2.  **Real-time Metrics**: KPIs update every 30 seconds
3.  **Interactive Charts**: Hover for detailed info
4.  **AI Analysis**: Click "Generate AI Analysis" for insights
5.  **Data Export**: Download detailed breakdowns

[Back to Top](#-table-of-contents)

---

## 🔧 Configuration

### Watcher Configuration (`watcher/config.py`)

```python
# Sample interval
SAMPLE_INTERVAL = 1  # seconds

# Session creation interval
FLUSH_INTERVAL = 30  # seconds

# Auto-idle threshold
IDLE_THRESHOLD = 300  # 5 minutes

# Customize application categories
PRIMARY_WORK_APPS = {
    "code.exe": "VSCode",
    "cursor.exe": "Cursor",
    # Add your apps here
}

# Customize work domains
WORK_DOMAINS = [
    "github.com",
    "stackoverflow.com",
    # Add your domains here
]
```

### Dashboard Configuration (`dashboard/config.py`)

```python
# Default date range
DEFAULT_DATE_RANGE = 7  # days

# Focus session thresholds
FOCUS_SESSION_MIN_DURATION = 600  # 10 minutes
FOCUS_SESSION_MIN_FOREGROUND = 0.8  # 80% active

# Productivity score thresholds
EXCELLENT_SCORE = 85
GOOD_SCORE = 70
MEDIUM_SCORE = 50
```

[Back to Top](#-table-of-contents)

---

## Database Schema

### Sessions Table
- **Tracks**: Every 30-second window
- **Categories**: `PRIMARY_WORK`, `SECONDARY_WORK`, `BROWSER_WORK`, `BROWSER_NONWORK`, `IDLE`
- **Metrics**: Duration, foreground time, productivity score, focus session flag

### Idle Periods Table
- **Tracks**: Manual and automatic idle periods
- **Reason**: Manual, auto, shutdown

### System Events Table
- **Logs**: Startup, shutdown, pause, resume events

[Back to Top](#-table-of-contents)

---

## Docker Notes

### Why Watcher Runs on Host
Docker containers **cannot access Windows GUI APIs** (pygetwindow, keyboard). The watcher must run natively on Windows to:
- Detect active window titles
- Capture keyboard shortcuts
- Show system tray icon

The dashboard runs perfectly in Docker as it only needs database access.

### Docker Commands

```bash
# Start dashboard only
docker-compose up dashboard

# View logs
docker-compose logs -f dashboard

# Rebuild after changes
docker-compose up --build dashboard

# Stop services
docker-compose down
```

[Back to Top](#-table-of-contents)

---

## Productivity Metrics Explained

### Focus Score (0-100)
Measures concentration quality:
- **85-100**: Excellent - Deep work dominates
- **70-84**: Good - Solid focus with minor distractions
- **50-69**: Medium - Fragmented attention
- **0-49**: Poor - High distraction level

**Formula**: `(Primary Work Ratio × 60) + (Focus Quality × 40)`

### Efficiency Score (0-100)
Percentage of tracked time spent on work:
- **Work** = `PRIMARY_WORK` + `SECONDARY_WORK` + `BROWSER_WORK`
- **Formula**: `(Work Time / Total Time) × 100`

### Time ROI (0-300+)
Value generated per minute tracked:
- **Primary Work**: 3x multiplier
- **Browser Work**: 1x multiplier
- **Secondary Work**: 0.8x multiplier
- **Formula**: `(Weighted Value / Total Time) × 100`

### Deep Work Sessions
Continuous `PRIMARY_WORK` periods with:
- Duration ≥ 10 minutes
- Foreground ratio ≥ 80%
- Minimal context switches

[Back to Top](#-table-of-contents)

---

## Privacy & Security

- **Local Data**: All data stays local in a SQLite database on your machine.
- **No Telemetry**: Zero data leaves your system (except AI API calls).
- **Gemini API**: Only sends aggregated metrics, not raw data.
- **Open Source**: Audit the code yourself.

[Back to Top](#-table-of-contents)

---

## Troubleshooting

### Watcher Issues

**Problem**: Hotkeys not working
- **Solution**: Run as administrator.

**Problem**: No data recorded
- **Solution**: Check logs in `~/ActivityTracker/logs/watcher.log`.

**Problem**: High CPU usage
- **Solution**: Increase `SAMPLE_INTERVAL` in config.

### Dashboard Issues

**Problem**: Database not found
- **Solution**: Ensure watcher has run for at least 30 seconds.

**Problem**: Charts not loading
- **Solution**: Wait for more data (minimum 1 hour recommended).

**Problem**: AI insights unavailable
- **Solution**: Add `GEMINI_API_KEY` to `.env` file.

[Back to Top](#-table-of-contents)

---

## Roadmap

- [ ] Web-based configuration UI
- [ ] Export reports to PDF
- [ ] Integration with Google Calendar
- [ ] Mobile companion app
- [ ] Team analytics (multi-user)
- [ ] Browser extension
- [ ] Pomodoro timer integration

[Back to Top](#-table-of-contents)

---

## Contributing

Contributions are welcome! Please follow these steps:
1.  Fork the repository.
2.  Create a feature branch (`git checkout -b feature/AmazingFeature`).
3.  Commit your changes (`git commit -m 'Add some AmazingFeature'`).
4.  Push to the branch (`git push origin feature/AmazingFeature`).
5.  Open a Pull Request.

[Back to Top](#-table-of-contents)

---

## License

Distributed under the MIT License. See `LICENSE` for more information.

[Back to Top](#-table-of-contents)

---

## Acknowledgments

- [Streamlit](https://streamlit.io/) for the amazing dashboard framework.
- [Plotly](https://plotly.com/) for interactive visualizations.
- [Google Gemini](https://deepmind.google/technologies/gemini/) for AI capabilities.

[Back to Top](#-table-of-contents)

---

## Support

- **Issues**: [GitHub Issues](https://github.com/aliasghar5642/Activity-Tracker/issues)
- **Discussions**: [GitHub Discussions](https://github.com/aliasghar5642/Activity-Tracker/discussions)
- **LinkedIn**: [LinkedIn Account](https://www.linkedin.com/in/aliasgharbagheri/)

---

**Built with ❤️ for productivity enthusiasts**

*Track smart. Work smarter. Live better.*
