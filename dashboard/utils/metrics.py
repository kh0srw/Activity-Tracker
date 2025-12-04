"""
Metrics Calculation Utilities - Simplified
Only: Total Active Time, Break Time, Time per Application
"""
import pandas as pd
from datetime import datetime


class MetricsCalculator:
    def __init__(self, df_activities, df_breaks=None):
        self.df = df_activities
        self.df_breaks = df_breaks
        
    def calculate_all_metrics(self):
        """Calculate simplified metrics"""
        return {
            **self.calculate_time_totals(),
            **self.calculate_app_summary(),
        }
    
    def calculate_time_totals(self):
        """Calculate total active time and break time"""
        # Total active time from activities
        total_active_seconds = self.df['duration_seconds'].sum()
        total_active_min = total_active_seconds / 60.0
        total_active_hours = total_active_seconds / 3600.0
        
        # Total break time
        total_break_seconds = 0
        total_break_min = 0
        total_break_hours = 0
        
        if self.df_breaks is not None and not self.df_breaks.empty:
            total_break_seconds = self.df_breaks['duration_seconds'].sum()
            total_break_min = total_break_seconds / 60.0
            total_break_hours = total_break_seconds / 3600.0
        
        # Total system time (active + breaks)
        total_system_seconds = total_active_seconds + total_break_seconds
        total_system_min = total_system_seconds / 60.0
        total_system_hours = total_system_seconds / 3600.0
        
        return {
            'total_active_seconds': round(total_active_seconds),
            'total_active_min': round(total_active_min, 1),
            'total_active_hours': round(total_active_hours, 2),
            
            'total_break_seconds': round(total_break_seconds),
            'total_break_min': round(total_break_min, 1),
            'total_break_hours': round(total_break_hours, 2),
            
            'total_system_seconds': round(total_system_seconds),
            'total_system_min': round(total_system_min, 1),
            'total_system_hours': round(total_system_hours, 2),
        }
    
    def calculate_app_summary(self):
        """Get summary of application count"""
        unique_apps = self.df['app_name'].nunique()
        
        return {
            'unique_apps': unique_apps,
        }
    
    def get_daily_breakdown(self):
        """Get daily breakdown of activities"""
        daily = self.df.groupby('date').agg({
            'duration_min': 'sum',
            'app_name': 'nunique',
        }).rename(columns={
            'duration_min': 'active_min',
            'app_name': 'apps_used'
        })
        
        # Add break time per day
        if self.df_breaks is not None and not self.df_breaks.empty:
            daily_breaks = self.df_breaks.groupby('date')['duration_min'].sum()
            daily_breaks.name = 'break_min'
            daily = daily.join(daily_breaks, how='left').fillna(0)
        else:
            daily['break_min'] = 0
        
        daily = daily.sort_index(ascending=False)
        
        return daily
    
    def get_hourly_breakdown(self):
        """Get hourly activity pattern"""
        hourly = self.df.groupby('hour').agg({
            'duration_min': 'sum',
            'app_name': 'nunique',
        }).rename(columns={
            'duration_min': 'active_min',
            'app_name': 'apps_used'
        })
        
        return hourly
    
    def get_app_breakdown(self):
        """
        Get aggregated time per application.
        This is the main view - total time per app, not individual sessions.
        """
        app_stats = self.df.groupby('app_name').agg({
            'duration_seconds': 'sum',
            'duration_min': 'sum',
            'id': 'count',
        }).rename(columns={
            'id': 'session_count',
        })
        
        # Add percentage
        total_min = app_stats['duration_min'].sum()
        app_stats['percentage'] = (app_stats['duration_min'] / total_min * 100).round(1)
        
        # Format hours
        app_stats['duration_hours'] = (app_stats['duration_min'] / 60).round(2)
        
        app_stats = app_stats.sort_values('duration_min', ascending=False)
        
        return app_stats
    
    def get_app_breakdown_by_date(self, target_date):
        """
        Get aggregated time per application for a specific date.
        """
        day_data = self.df[self.df['date'] == target_date]
        
        if day_data.empty:
            return pd.DataFrame()
        
        app_stats = day_data.groupby('app_name').agg({
            'duration_seconds': 'sum',
            'duration_min': 'sum',
        })
        
        # Add percentage
        total_min = app_stats['duration_min'].sum()
        app_stats['percentage'] = (app_stats['duration_min'] / total_min * 100).round(1)
        app_stats['duration_hours'] = (app_stats['duration_min'] / 60).round(2)
        
        app_stats = app_stats.sort_values('duration_min', ascending=False)
        
        return app_stats
