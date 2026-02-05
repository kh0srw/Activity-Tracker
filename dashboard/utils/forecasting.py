import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class ActivityForecaster:
    def __init__(self, df_activities, df_breaks):
        """
        Initialize the forecaster with activity and break dataframes.
        """
        # Create copies to avoid modifying the original dataframes
        self.df_activities = df_activities.copy() if df_activities is not None else None
        self.df_breaks = df_breaks.copy() if df_breaks is not None else None
        
        # Ensure start_time exists in activities
        self._ensure_start_time(self.df_activities)
        
        # Ensure start_time exists in breaks
        self._ensure_start_time(self.df_breaks)

        self.daily_stats = self._calculate_daily_stats()

    def _ensure_start_time(self, df):
        """Helper to ensure a 'start_time' column exists."""
        if df is not None and not df.empty and 'start_time' not in df.columns:
            # If index is datetime, use it
            if isinstance(df.index, pd.DatetimeIndex):
                df['start_time'] = df.index
            # If 'timestamp' exists, use it
            elif 'timestamp' in df.columns:
                df['start_time'] = pd.to_datetime(df['timestamp'])

    def _calculate_daily_stats(self):
        """Aggregates raw data into daily totals for forecasting."""
        if self.df_activities is None or self.df_activities.empty:
            return pd.DataFrame()

        # Group activities by day
        # Ensure start_time is datetime
        if not pd.api.types.is_datetime64_any_dtype(self.df_activities['start_time']):
             self.df_activities['start_time'] = pd.to_datetime(self.df_activities['start_time'])

        self.df_activities['date'] = self.df_activities['start_time'].dt.date
        daily_active = self.df_activities.groupby('date')['duration_min'].sum().reset_index()
        daily_active.columns = ['date', 'active_min']

        # Group breaks by day
        daily_break = pd.DataFrame(columns=['date', 'break_min'])
        if self.df_breaks is not None and not self.df_breaks.empty:
            # Ensure start_time is datetime for breaks
            if not pd.api.types.is_datetime64_any_dtype(self.df_breaks['start_time']):
                self.df_breaks['start_time'] = pd.to_datetime(self.df_breaks['start_time'])

            self.df_breaks['date'] = self.df_breaks['start_time'].dt.date
            daily_break = self.df_breaks.groupby('date')['duration_min'].sum().reset_index()
            daily_break.columns = ['date', 'break_min']

        # Merge
        stats = pd.merge(daily_active, daily_break, on='date', how='outer').fillna(0)
        stats['active_hours'] = stats['active_min'] / 60
        stats['break_hours'] = stats['break_min'] / 60
        stats['total_hours'] = stats['active_hours'] + stats['break_hours']
        
        # Sort by date
        stats = stats.sort_values('date')
        return stats

    def get_daily_totals(self):
        """Returns the historical daily totals."""
        return self.daily_stats

    def _predict_next_value(self, series, method='weighted_avg'):
        """Simple prediction logic using weighted average of recent days."""
        if len(series) < 3:
            return series.mean()
        
        # Give more weight to recent data
        weights = np.linspace(1, 2, len(series))
        return np.average(series, weights=weights)

    def forecast_short_term(self, days_ahead=7):
        """
        Generates a daily forecast for the next N working days.
        FIX: Starts from Tomorrow.
        FIX: Skips Fridays and Weekends.
        """
        if self.daily_stats.empty or len(self.daily_stats) < 3:
            return None

        # Calculate historical stats for comparison
        avg_active = self.daily_stats['active_hours'].mean()
        avg_break = self.daily_stats['break_hours'].mean()
        
        # Determine trend
        recent_active = self.daily_stats['active_hours'].tail(5)
        trend_val = np.polyfit(range(len(recent_active)), recent_active, 1)[0]
        trend = "increasing" if trend_val > 0.1 else "decreasing" if trend_val < -0.1 else "stable"

        stats = {
            'avg_active': avg_active,
            'avg_break': avg_break,
            'trend_active': trend
        }

        # Generate forecast dates
        forecast_data = []
        
        # FIX: Start from TOMORROW, not today
        current_date = datetime.now().date() + timedelta(days=1)
        days_generated = 0
        
        # Base predictions on recent history (last 14 days)
        recent_history = self.daily_stats.tail(14)
        base_active = self._predict_next_value(recent_history['active_hours'].values)
        base_break = self._predict_next_value(recent_history['break_hours'].values)

        while days_generated < days_ahead:
            # FIX: 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun
            # Skip Friday (4), Saturday (5), Sunday (6)
            if current_date.weekday() in [4, 5, 6]:
                current_date += timedelta(days=1)
                continue

            # Add slight random variation for realism based on std dev
            std_active = recent_history['active_hours'].std() if len(recent_history) > 1 else 0.5
            noise = np.random.normal(0, std_active * 0.2)
            
            pred_active = max(0.5, base_active + noise) # Minimum 30 mins
            pred_break = max(0.1, base_break + (noise * 0.3))

            forecast_data.append({
                'date': current_date,
                'active_hours': pred_active,
                'break_hours': pred_break,
                'type': 'Forecast'
            })
            
            current_date += timedelta(days=1)
            days_generated += 1

        forecast_df = pd.DataFrame(forecast_data)
        
        # Prepare historical data for charting (last 14 days)
        historical_df = self.daily_stats.tail(14).copy()
        historical_df['type'] = 'Historical'
        
        return forecast_df, historical_df, stats

    def forecast_long_term(self, months_ahead=3):
        """Generates a monthly aggregated forecast."""
        if self.daily_stats.empty:
            return None

        # Aggregate history by week for context
        self.daily_stats['date'] = pd.to_datetime(self.daily_stats['date'])
        weekly_hist = self.daily_stats.resample('W-MON', on='date')[['active_hours', 'break_hours']].sum().reset_index()
        
        # Simple projection
        avg_monthly_active = self.daily_stats['active_hours'].mean() * 20 # approx 20 work days (excluding Fridays)
        avg_monthly_break = self.daily_stats['break_hours'].mean() * 20
        
        forecast_data = []
        current_date = datetime.now().replace(day=1) + timedelta(days=32) # Next month start
        
        for _ in range(months_ahead):
            forecast_data.append({
                'month_name': current_date.strftime("%B %Y"),
                'active_hours': avg_monthly_active,
                'break_hours': avg_monthly_break,
                'total_hours': avg_monthly_active + avg_monthly_break
            })
            current_date += timedelta(days=32)
        
        monthly_forecast = pd.DataFrame(forecast_data)
        
        # Reuse stats from short term
        stats = {
            'trend_active': 'stable' # simplified
        }
        
        return monthly_forecast, weekly_hist, stats

    def get_app_forecast(self, days_ahead=7, top_n=5):
        """Predicts usage trends for top applications."""
        if self.df_activities is None or self.df_activities.empty:
            return None

        # Get top apps
        top_apps = self.df_activities.groupby('app_name')['duration_min'].sum().nlargest(top_n).index.tolist()
        
        app_forecasts = []
        
        for app in top_apps:
            app_data = self.df_activities[self.df_activities['app_name'] == app].copy()
            # Ensure proper datetime format
            app_data['date'] = app_data['start_time'].dt.date
            daily_app = app_data.groupby('date')['duration_min'].sum()
            
            if len(daily_app) < 2:
                continue
                
            current_avg_hours = daily_app.mean() / 60
            
            # Simple trend
            trend_val = 0
            if len(daily_app) >= 3:
                y = daily_app.values
                x = range(len(y))
                trend_val = np.polyfit(x, y, 1)[0]
            
            trend_str = "increasing" if trend_val > 5 else "decreasing" if trend_val < -5 else "stable"
            
            # Project
            forecast_avg = current_avg_hours + (trend_val * days_ahead / 60)
            forecast_avg = max(0, forecast_avg)

            app_forecasts.append({
                'app_name': app,
                'current_avg': current_avg_hours,
                'forecast_avg': forecast_avg,
                'trend': trend_str
            })
            
        return pd.DataFrame(app_forecasts)

    def get_insights(self):
        """Generates simple text insights based on data."""
        insights = []
        
        if self.daily_stats.empty:
            return insights

        avg_active = self.daily_stats['active_hours'].mean()
        
        if avg_active > 8:
            insights.append({
                'type': 'warning',
                'title': 'High Workload',
                'message': 'You are consistently averaging over 8 hours. Consider reducing hours to prevent burnout.'
            })
        elif avg_active < 4:
            insights.append({
                'type': 'info',
                'title': 'Light Load',
                'message': 'Activity levels are lower than standard full-time hours.'
            })
            
        # Check breaks
        avg_break_ratio = self.daily_stats['break_hours'].sum() / (self.daily_stats['total_hours'].sum() + 0.001)
        if avg_break_ratio < 0.1:
            insights.append({
                'type': 'warning',
                'title': 'Take More Breaks',
                'message': 'Your break time is less than 10% of your total time. Try the 52/17 rule.'
            })
        else:
            insights.append({
                'type': 'positive',
                'title': 'Healthy Break Habits',
                'message': 'You are maintaining a good balance of break times.'
            })

        return insights