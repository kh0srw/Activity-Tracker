"""
Data Loading Utilities - Simplified
"""
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class DataLoader:
    def __init__(self, db_path):
        self.db_path = db_path
        
    def get_connection(self):
        """Get database connection with timeout"""
        return sqlite3.connect(self.db_path, timeout=30)
    
    def load_activities(self, days=30):
        """Load all activity data from database"""
        try:
            query = """
                SELECT 
                    id,
                    timestamp,
                    process_name,
                    window_title,
                    duration_seconds
                FROM activity_log
                WHERE timestamp >= datetime('now', ?)
                ORDER BY timestamp DESC
            """
            
            conn = self.get_connection()
            df = pd.read_sql_query(query, conn, params=(f'-{days} days',))
            conn.close()
            
            if df.empty:
                return None
                
            # Data preprocessing
            df['timestamp_dt'] = pd.to_datetime(df['timestamp'])
            df['duration_min'] = df['duration_seconds'] / 60.0
            df['date'] = df['timestamp_dt'].dt.date
            df['hour'] = df['timestamp_dt'].dt.hour
            
            # Clean process name for display
            df['app_name'] = df['process_name'].str.replace('.exe', '', case=False, regex=False)
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to load activities: {e}")
            return None
    
    def load_breaks(self, days=30):
        """Load break/pause data"""
        try:
            query = """
                SELECT 
                    id,
                    start_time,
                    end_time,
                    duration_seconds
                FROM breaks
                WHERE start_time >= datetime('now', ?)
                ORDER BY start_time DESC
            """
            
            conn = self.get_connection()
            df = pd.read_sql_query(query, conn, params=(f'-{days} days',))
            conn.close()
            
            if df.empty:
                return None
                
            df['start_dt'] = pd.to_datetime(df['start_time'])
            df['end_dt'] = pd.to_datetime(df['end_time'])
            df['duration_min'] = df['duration_seconds'] / 60.0
            df['date'] = df['start_dt'].dt.date
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to load breaks: {e}")
            return None
    
    def get_database_stats(self):
        """Get database statistics"""
        try:
            conn = self.get_connection()
            c = conn.cursor()
            
            stats = {}
            
            # Total activities
            c.execute("SELECT COUNT(*) FROM activity_log")
            stats['total_activities'] = c.fetchone()[0]
            
            # Date range
            c.execute("SELECT MIN(timestamp), MAX(timestamp) FROM activity_log")
            result = c.fetchone()
            if result[0]:
                stats['first_activity'] = result[0]
                stats['last_activity'] = result[1]
            
            # Total time tracked
            c.execute("SELECT SUM(duration_seconds) FROM activity_log")
            total_seconds = c.fetchone()[0] or 0
            stats['total_hours_tracked'] = total_seconds / 3600.0
            
            # Total breaks
            c.execute("SELECT COUNT(*), SUM(duration_seconds) FROM breaks")
            result = c.fetchone()
            stats['total_breaks'] = result[0] or 0
            stats['total_break_hours'] = (result[1] or 0) / 3600.0
            
            conn.close()
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {}
