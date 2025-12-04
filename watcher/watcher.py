"""
Activity Tracker - Simple Raw Window Tracker
Tracks ALL active windows without any filtering or categorization
"""

import os
import sys
import time
import threading
import logging
import sqlite3
from datetime import datetime
from queue import Queue, Empty

try:
    import win32gui
    import win32process
    import psutil
    from pynput import keyboard as pynput_keyboard
    import pystray
    from pystray import MenuItem as item
    from PIL import Image, ImageDraw
    import winsound
    WINDOWS_FEATURES = True
except ImportError:
    WINDOWS_FEATURES = False
    print("Error: Windows features required. Install: pip install pywin32 psutil pynput pystray pillow")
    sys.exit(1)

import config

# Logging setup
logging.basicConfig(
    filename=config.LOG_DIR / "watcher.log",
    level=getattr(logging, config.LOG_LEVEL),
    format="%(asctime)s | %(levelname)s | %(message)s",
    encoding="utf-8"
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger().addHandler(console)


class HotkeyManager:
    """
    Dedicated hotkey manager running on its own thread.
    Uses a command queue to communicate with the main watcher.
    """
    
    def __init__(self, command_queue: Queue):
        self.command_queue = command_queue
        self.listener = None
        self.thread = None
        self.running = False
    
    def start(self):
        """Start the hotkey listener on a dedicated thread"""
        self.running = True
        self.thread = threading.Thread(target=self._run_listener, daemon=True, name="HotkeyThread")
        self.thread.start()
        logging.info("Hotkey listener started on dedicated thread")
    
    def stop(self):
        """Stop the hotkey listener"""
        self.running = False
        if self.listener:
            self.listener.stop()
    
    def _run_listener(self):
        """Run the keyboard listener (blocks on this thread)"""
        try:
            self.listener = pynput_keyboard.GlobalHotKeys({
                '<ctrl>+<alt>+<shift>+p': self._on_toggle_pause,
            })
            self.listener.start()
            
            # Keep thread alive while running
            while self.running:
                time.sleep(0.1)
                
        except Exception as e:
            logging.error(f"Hotkey listener error: {e}")
    
    def _on_toggle_pause(self):
        """Handle toggle pause hotkey - just queue the command"""
        try:
            self.command_queue.put_nowait("TOGGLE_PAUSE")
        except Exception as e:
            logging.error(f"Failed to queue command: {e}")


class DatabaseWriter:
    """
    Non-blocking database writer using a separate thread.
    Prevents DB operations from blocking the main loop.
    """
    
    def __init__(self, db_path):
        self.db_path = db_path
        self.write_queue = Queue()
        self.thread = None
        self.running = False
    
    def start(self):
        """Start the database writer thread"""
        self.running = True
        self.thread = threading.Thread(target=self._process_writes, daemon=True, name="DBWriterThread")
        self.thread.start()
        logging.info("Database writer thread started")
    
    def stop(self):
        """Stop the writer and flush remaining items"""
        self.running = False
        # Process remaining items
        while not self.write_queue.empty():
            try:
                item = self.write_queue.get_nowait()
                self._execute_write(item)
            except Empty:
                break
    
    def queue_activity(self, timestamp, process_name, window_title, duration_seconds):
        """Queue an activity record for writing"""
        self.write_queue.put({
            'type': 'activity',
            'timestamp': timestamp,
            'process_name': process_name,
            'window_title': window_title,
            'duration_seconds': duration_seconds
        })
    
    def queue_break(self, start_time, end_time, duration_seconds):
        """Queue a break record for writing"""
        self.write_queue.put({
            'type': 'break',
            'start_time': start_time,
            'end_time': end_time,
            'duration_seconds': duration_seconds
        })
    
    def queue_event(self, event_type, details=None):
        """Queue a system event for writing"""
        self.write_queue.put({
            'type': 'event',
            'event_type': event_type,
            'timestamp': datetime.now().isoformat(),
            'details': details
        })
    
    def _process_writes(self):
        """Process write queue continuously"""
        while self.running:
            try:
                item = self.write_queue.get(timeout=1.0)
                self._execute_write(item)
            except Empty:
                continue
            except Exception as e:
                logging.error(f"DB write error: {e}")
    
    def _execute_write(self, item):
        """Execute a single write operation"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            if item['type'] == 'activity':
                c.execute("""
                    INSERT INTO activity_log (timestamp, process_name, window_title, duration_seconds)
                    VALUES (?, ?, ?, ?)
                """, (
                    item['timestamp'],
                    item['process_name'],
                    item['window_title'],
                    item['duration_seconds']
                ))
            
            elif item['type'] == 'break':
                c.execute("""
                    INSERT INTO breaks (start_time, end_time, duration_seconds)
                    VALUES (?, ?, ?)
                """, (
                    item['start_time'],
                    item['end_time'],
                    item['duration_seconds']
                ))
            
            elif item['type'] == 'event':
                c.execute("""
                    INSERT INTO system_events (event_type, timestamp, details)
                    VALUES (?, ?, ?)
                """, (
                    item['event_type'],
                    item['timestamp'],
                    item['details']
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logging.error(f"DB execute error: {e}")


class SimpleActivityWatcher:
    """
    Simple activity watcher - tracks ALL windows without filtering.
    No categorization, no productivity scoring, just raw data.
    """
    
    def __init__(self):
        self.db_path = config.DB_PATH
        self.monitoring = True
        self.is_paused = False
        
        # Current tracking state
        self.current_process = None
        self.current_window = None
        self.current_start = None
        
        # Pause tracking
        self.pause_start = None
        
        # Command queue for hotkey communication
        self.command_queue = Queue()
        
        # Components
        self.hotkey_manager = HotkeyManager(self.command_queue)
        self.db_writer = DatabaseWriter(self.db_path)
        
        self.icon = None
        self.polling_thread = None
        self.command_thread = None
        
        # Initialize
        self.init_db()
        
        logging.info("=" * 60)
        logging.info("Activity Tracker - RAW MODE (No Filtering)")
        logging.info(f"Database: {self.db_path}")
        logging.info("Tracking: ALL windows and processes")
        logging.info("Hotkey: Ctrl+Alt+Shift+P to pause/resume")
        logging.info("=" * 60)
    
    def init_db(self):
        """Initialize simplified database schema"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Activity log - raw tracking (no categories)
        c.execute("""
            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                process_name TEXT NOT NULL,
                window_title TEXT,
                duration_seconds REAL NOT NULL
            )
        """)
        
        # Breaks - manual pauses only
        c.execute("""
            CREATE TABLE IF NOT EXISTS breaks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_time TEXT NOT NULL,
                end_time TEXT,
                duration_seconds REAL
            )
        """)
        
        # System events for debugging
        c.execute("""
            CREATE TABLE IF NOT EXISTS system_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                details TEXT
            )
        """)
        
        # Indexes for faster queries
        c.execute("CREATE INDEX IF NOT EXISTS idx_activity_timestamp ON activity_log(timestamp)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_activity_process ON activity_log(process_name)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_breaks_start ON breaks(start_time)")
        
        conn.commit()
        conn.close()
        logging.info("Database initialized (simplified schema)")
    
    def beep(self, freq=1000, dur=200):
        """Audio feedback"""
        try:
            winsound.Beep(freq, dur)
        except:
            pass
    
    def toggle_pause(self):
        """Toggle pause state with audio and visual feedback"""
        try:
            if self.is_paused:
                # === RESUME TRACKING ===
                if self.pause_start:
                    duration = (datetime.now() - self.pause_start).total_seconds()
                    self.db_writer.queue_break(
                        self.pause_start.isoformat(),
                        datetime.now().isoformat(),
                        duration
                    )
                    logging.info(f"Break saved: {duration:.0f} seconds")
                
                self.is_paused = False
                self.pause_start = None
                self.current_start = datetime.now()  # Reset timing
                
                # Feedback
                self.beep(1500, 150)  # High pitch = resumed
                self.beep(1500, 150)  # Double beep for resume
                print("\n" + "=" * 40)
                print("▶️  TRACKING RESUMED")
                print("=" * 40 + "\n")
                logging.info("▶️ TRACKING RESUMED")
                
                self.db_writer.queue_event("TRACKING_RESUMED")
                
                # Update icon color
                if self.icon:
                    self.icon.icon = self.create_icon(config.ICON_COLOR_ACTIVE)
                
            else:
                # === PAUSE TRACKING ===
                self.save_current_activity()  # Save current before pausing
                
                self.is_paused = True
                self.pause_start = datetime.now()
                
                # Feedback
                self.beep(800, 300)  # Low pitch = paused
                print("\n" + "=" * 40)
                print("⏸️  TRACKING PAUSED")
                print("=" * 40 + "\n")
                logging.info("⏸️ TRACKING PAUSED")
                
                self.db_writer.queue_event("TRACKING_PAUSED")
                
                # Update icon color
                if self.icon:
                    self.icon.icon = self.create_icon(config.ICON_COLOR_PAUSED)
                
        except Exception as e:
            logging.error(f"Toggle pause error: {e}")
    
    def get_active_window(self):
        """Get current active window info - tracks EVERYTHING"""
        try:
            hwnd = win32gui.GetForegroundWindow()
            if hwnd == 0:
                return None, None
            
            window_title = win32gui.GetWindowText(hwnd)
            if not window_title:
                return None, None
            
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            proc = psutil.Process(pid)
            process_name = proc.name()
            
            return process_name, window_title
            
        except:
            return None, None
    
    def save_current_activity(self):
        """Save current activity to database"""
        if not self.current_process or not self.current_start:
            return
        
        duration = (datetime.now() - self.current_start).total_seconds()
        
        if duration < config.MIN_ACTIVITY_DURATION:
            return
        
        self.db_writer.queue_activity(
            self.current_start.isoformat(),
            self.current_process,
            self.current_window,
            duration
        )
        
        logging.debug(f"Activity saved: {self.current_process} | {duration:.1f}s")
    
    def process_commands(self):
        """Process commands from the hotkey manager"""
        while self.monitoring:
            try:
                cmd = self.command_queue.get(timeout=0.5)
                
                if cmd == "TOGGLE_PAUSE":
                    self.toggle_pause()
                    
            except Empty:
                continue
            except Exception as e:
                logging.error(f"Command processing error: {e}")
    
    def poll_window(self):
        """Main polling loop for active window - tracks EVERYTHING"""
        while self.monitoring:
            try:
                if self.is_paused:
                    time.sleep(0.5)
                    continue
                
                process_name, window_title = self.get_active_window()
                
                if not process_name:
                    time.sleep(0.5)
                    continue
                
                # Check if window changed
                if process_name != self.current_process or window_title != self.current_window:
                    # Save previous activity
                    self.save_current_activity()
                    
                    # Start tracking new activity
                    self.current_process = process_name
                    self.current_window = window_title
                    self.current_start = datetime.now()
                    
                    logging.debug(f"Window: {process_name} | {window_title[:50]}...")
                
                time.sleep(config.POLL_INTERVAL)
                
            except Exception as e:
                logging.error(f"Polling error: {e}")
                time.sleep(1)
    
    def create_icon(self, color):
        """Create system tray icon"""
        img = Image.new("RGB", (64, 64), color)
        d = ImageDraw.Draw(img)
        d.rectangle((12, 12, 52, 52), outline="white", width=4)
        return img
    
    def quit_app(self, icon=None, item=None):
        """Clean shutdown"""
        logging.info("Shutdown initiated")
        self.monitoring = False
        
        # Save any current activity
        self.save_current_activity()
        
        # Save any pending break
        if self.is_paused and self.pause_start:
            duration = (datetime.now() - self.pause_start).total_seconds()
            self.db_writer.queue_break(
                self.pause_start.isoformat(),
                datetime.now().isoformat(),
                duration
            )
        
        # Log shutdown event
        self.db_writer.queue_event("SYSTEM_SHUTDOWN")
        
        # Stop components
        self.hotkey_manager.stop()
        self.db_writer.stop()
        
        if self.icon:
            self.icon.stop()
        
        logging.info("Shutdown complete")
        os._exit(0)
    
    def run(self):
        """Start the watcher"""
        # Log startup
        self.db_writer.start()
        self.db_writer.queue_event("SYSTEM_STARTUP")
        
        # Start hotkey manager
        self.hotkey_manager.start()
        
        # Start command processor thread
        self.command_thread = threading.Thread(target=self.process_commands, daemon=True, name="CommandThread")
        self.command_thread.start()
        
        # Start polling thread
        self.polling_thread = threading.Thread(target=self.poll_window, daemon=True, name="PollingThread")
        self.polling_thread.start()
        
        # System tray menu
        menu = (
            item("Pause/Resume (Ctrl+Alt+Shift+P)", lambda: self.command_queue.put("TOGGLE_PAUSE")),
            item("Exit", self.quit_app)
        )
        
        self.icon = pystray.Icon(
            "ActivityTracker",
            self.create_icon(config.ICON_COLOR_ACTIVE),
            "Activity Tracker (Tracking)",
            menu
        )
        
        print("\n" + "=" * 50)
        print("🟢 Activity Tracker Running")
        print("   Press Ctrl+Alt+Shift+P to pause/resume")
        print("=" * 50 + "\n")
        
        # Run system tray (blocks)
        self.icon.run()


if __name__ == "__main__":
    if not WINDOWS_FEATURES:
        print("Error: Windows-specific libraries required")
        sys.exit(1)
    
    watcher = SimpleActivityWatcher()
    watcher.run()
