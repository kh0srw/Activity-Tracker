"""
Activity Tracker - Simple Dashboard
Shows: Total Active Time, Break Time, Time per Application
NEW: Future Outlook with Forecasting
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date
import os
import logging
import numpy as np

import config
from utils.data_loader import DataLoader
from utils.metrics import MetricsCalculator
from utils.visualizations import *
from utils.forecasting import ActivityForecaster
from utils.visualizations_forecast import *


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page config
st.set_page_config(
    page_title=config.PAGE_TITLE,
    page_icon=config.PAGE_ICON,
    layout=config.LAYOUT,
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    /* Main styling */
    .main-header {
        font-size: 3rem;
        font-weight: 800;
        background: linear-gradient(120deg, #10B981 0%, #3B82F6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    
    .subtitle {
        font-size: 1.1rem;
        color: #6B7280;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    /* Big metric cards */
    .big-metric {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 16px;
        text-align: center;
        color: white;
        margin-bottom: 1rem;
    }
    
    .big-metric-value {
        font-size: 3rem;
        font-weight: bold;
        margin: 0;
    }
    
    .big-metric-label {
        font-size: 1rem;
        opacity: 0.9;
        margin-top: 0.5rem;
    }
    
    /* Active metric */
    .metric-active {
        background: linear-gradient(135deg, #10B981 0%, #059669 100%);
    }
    
    /* Break metric */
    .metric-break {
        background: linear-gradient(135deg, #F59E0B 0%, #D97706 100%);
    }
    
    /* System metric */
    .metric-system {
        background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%);
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1F2937 0%, #111827 100%);
    }
    
    section[data-testid="stSidebar"] .stMarkdown {
        color: white;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* App table */
    .app-table {
        background: white;
        border-radius: 8px;
        padding: 1rem;
    }
</style>
""", unsafe_allow_html=True)


def format_duration(minutes):
    """Format minutes into hours and minutes string"""
    if minutes < 60:
        return f"{minutes:.0f}m"
    hours = minutes // 60
    mins = minutes % 60
    if mins > 0:
        return f"{hours:.0f}h {mins:.0f}m"
    return f"{hours:.0f}h"


class ActivityDashboard:
    def __init__(self):
        self.db_path = config.DB_PATH
        
        # Check database
        if not os.path.exists(self.db_path):
            st.error("❌ Database not found!")
            st.info(f"Expected location: `{self.db_path}`\n\nPlease run the **Activity Watcher** first.")
            st.stop()
        
        # Initialize data loader
        self.loader = DataLoader(self.db_path)
        
        # Session state
        if 'date_range' not in st.session_state:
            st.session_state.date_range = config.DEFAULT_DATE_RANGE
    
    def load_data(self, days):
        """Load and prepare all data"""
        with st.spinner("Loading activity data..."):
            df_activities = self.loader.load_activities(days)
            df_breaks = self.loader.load_breaks(days)
            
            if df_activities is None or df_activities.empty:
                return None, None, None, None
            
            metrics_calc = MetricsCalculator(df_activities, df_breaks)
            metrics = metrics_calc.calculate_all_metrics()
            
            return df_activities, df_breaks, metrics_calc, metrics
    
    def render_header(self):
        """Render dashboard header"""
        st.markdown("<h1 class='main-header'>Activity Tracker</h1>", unsafe_allow_html=True)
        st.markdown(
            "<p class='subtitle'>📊 Simple tracking • No categories • Just time</p>",
            unsafe_allow_html=True
        )
    
    def render_sidebar(self):
        """Render sidebar controls"""
        with st.sidebar:
            st.markdown("## ⚙️ Controls")
            
            # Date range selector
            date_range = st.selectbox(
                "Time Period",
                options=[1, 3, 7, 14, 30],
                index=2,
                format_func=lambda x: f"Last {x} day{'s' if x > 1 else ''}"
            )
            
            st.session_state.date_range = date_range
            
            # Refresh button
            if st.button("🔄 Refresh Data", use_container_width=True):
                st.rerun()
            
            st.markdown("---")
            
            # Database stats
            st.markdown("### 📊 Database Info")
            stats = self.loader.get_database_stats()
            
            if stats:
                st.metric("Total Activities", f"{stats.get('total_activities', 0):,}")
                st.metric("Hours Tracked", f"{stats.get('total_hours_tracked', 0):.1f}")
                st.metric("Total Breaks", stats.get('total_breaks', 0))
                
                if 'first_activity' in stats:
                    st.caption(f"Tracking since: {stats['first_activity'][:10]}")
            
            st.markdown("---")
            
            # Hotkey reference
            st.markdown("### ⌨️ Watcher Control")
            st.code("Ctrl+Alt+Shift+P → Pause/Resume")
            
            st.markdown("---")
            st.caption(f"DB: `{os.path.basename(self.db_path)}`")
    
    def render_main_metrics(self, metrics):
        """Render the three main metrics: Active Time, Break Time, Total System Time"""
        st.markdown("### 📈 Time Summary")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            active_hours = metrics['total_active_hours']
            active_min = metrics['total_active_min']
            st.markdown(f"""
                <div class='big-metric metric-active'>
                    <p class='big-metric-value'>{format_duration(active_min)}</p>
                    <p class='big-metric-label'>🖥️ Active Time</p>
                </div>
            """, unsafe_allow_html=True)
        
        with col2:
            break_min = metrics['total_break_min']
            st.markdown(f"""
                <div class='big-metric metric-break'>
                    <p class='big-metric-value'>{format_duration(break_min)}</p>
                    <p class='big-metric-label'>☕ Break Time</p>
                </div>
            """, unsafe_allow_html=True)
        
        with col3:
            system_min = metrics['total_system_min']
            st.markdown(f"""
                <div class='big-metric metric-system'>
                    <p class='big-metric-value'>{format_duration(system_min)}</p>
                    <p class='big-metric-label'>📊 Total System Time</p>
                </div>
            """, unsafe_allow_html=True)
        
        # Additional stats row
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Unique Applications", metrics['unique_apps'])
        with col2:
            if metrics['total_system_min'] > 0:
                active_pct = (metrics['total_active_min'] / metrics['total_system_min']) * 100
                st.metric("Active Ratio", f"{active_pct:.0f}%")
    
    def render_app_breakdown(self, metrics_calc):
        """Render time per application - the main view"""
        st.markdown("---")
        st.markdown("## 💻 Time per Application")
        
        app_stats = metrics_calc.get_app_breakdown()
        
        if app_stats.empty:
            st.info("No application data available")
            return
        
        # Chart and table side by side
        col1, col2 = st.columns([2, 1])
        
        with col1:
            fig = create_app_breakdown_chart(app_stats, top_n=15)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Top apps pie chart
            fig = create_app_pie_chart(app_stats, top_n=8)
            st.plotly_chart(fig, use_container_width=True)
        
        # Detailed table
        st.markdown("### 📋 Detailed Breakdown")
        
        display_df = app_stats[['duration_min', 'duration_hours', 'percentage']].copy()
        display_df.columns = ['Minutes', 'Hours', 'Percentage']
        
        st.dataframe(
            display_df.style.format({
                'Minutes': '{:.0f}',
                'Hours': '{:.2f}',
                'Percentage': '{:.1f}%'
            }),
            use_container_width=True
        )
    
    def render_charts(self, df, metrics_calc, metrics):
        """Render additional charts"""
        st.markdown("---")
        st.markdown("## 📊 Activity Patterns")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Time allocation pie
            fig = create_time_pie(metrics)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Daily trend
            fig = create_daily_trend(metrics_calc)
            st.plotly_chart(fig, use_container_width=True)
        
        # Heatmap (full width)
        fig = create_hourly_heatmap(df)
        if fig.data:
            st.plotly_chart(fig, use_container_width=True)
    
    def render_daily_breakdown(self, metrics_calc):
        """Render daily breakdown table"""
        st.markdown("---")
        st.markdown("## 📅 Daily Breakdown")
        
        daily = metrics_calc.get_daily_breakdown()
        
        if daily.empty:
            st.info("No daily data available")
            return
        
        display_df = daily.copy()
        display_df.columns = ['Active (min)', 'Apps Used', 'Break (min)']
        
        st.dataframe(
            display_df.style.format({
                'Active (min)': '{:.0f}',
                'Break (min)': '{:.0f}'
            }),
            use_container_width=True
        )
    
    def render_forecast_section(self, df, df_breaks):
        """Render future forecast section"""
        st.markdown("---")
        st.markdown("## 🔮 Future Outlook")
        st.markdown("*Predictions based on your historical activity patterns*")
        
        forecaster = ActivityForecaster(df, df_breaks)
        
        # Check if we have enough data
        daily_totals = forecaster.get_daily_totals()
        if len(daily_totals) < 3:
            st.warning("⏳ Need at least 3 days of data for forecasting. Keep tracking!")
            return
        
        # Forecast type selector
        forecast_type = st.radio(
            "Select Forecast Horizon",
            options=['Short-Term', 'Long-Term'],
            horizontal=True,
            help="Short-term: Days/Weeks | Long-term: Months"
        )
        
        if forecast_type == 'Short-Term':
            self._render_short_term_forecast(forecaster)
        else:
            self._render_long_term_forecast(forecaster)
        
        # Insights section (always shown)
        self._render_insights(forecaster)
    
    def _render_short_term_forecast(self, forecaster):
        """Render short-term forecast"""
        st.markdown("### 📊 Short-Term Forecast")
        
        # Preset selector
        col1, col2 = st.columns([3, 1])
        with col1:
            preset = st.selectbox(
                "Forecast Period",
                options=[3, 7, 14, 30],
                format_func=lambda x: f"Next {x} days",
                index=1
            )
        
        result = forecaster.forecast_short_term(days_ahead=preset)
        
        if result is None:
            st.warning("Not enough data for forecasting")
            return
        
        forecast_df, historical_df, stats = result
        
        # Summary metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            avg_forecast_active = forecast_df['active_hours'].mean()
            current_avg = stats['avg_active']
            change = ((avg_forecast_active - current_avg) / current_avg * 100) if current_avg > 0 else 0
            
            st.metric(
                "Forecast Avg Active",
                f"{avg_forecast_active:.1f}h/day",
                f"{change:+.1f}%"
            )
        
        with col2:
            avg_forecast_break = forecast_df['break_hours'].mean()
            current_break = stats['avg_break']
            change_break = ((avg_forecast_break - current_break) / current_break * 100) if current_break > 0 else 0
            
            st.metric(
                "Forecast Avg Break",
                f"{avg_forecast_break:.1f}h/day",
                f"{change_break:+.1f}%"
            )
        
        with col3:
            trend_emoji = "📈" if stats['trend_active'] == 'increasing' else "📉" if stats['trend_active'] == 'decreasing' else "➡️"
            st.metric(
                "Activity Trend",
                stats['trend_active'].title(),
                f"{trend_emoji}"
            )
        
        # Main forecast chart
        fig = create_short_term_forecast_chart(forecast_df, historical_df)
        st.plotly_chart(fig, use_container_width=True)
        
        # Gauges
        col1, col2 = st.columns(2)
        with col1:
            fig_gauge = create_forecast_gauge(
                current_avg,
                avg_forecast_active,
                "Active Hours"
            )
            st.plotly_chart(fig_gauge, use_container_width=True)
        
        with col2:
            fig_gauge_break = create_forecast_gauge(
                current_break,
                avg_forecast_break,
                "Break Hours"
            )
            st.plotly_chart(fig_gauge_break, use_container_width=True)
        
        # App-level forecast
        st.markdown("#### 📱 Top Applications Forecast")
        app_forecast = forecaster.get_app_forecast(days_ahead=preset, top_n=5)
        
        if app_forecast is not None and not app_forecast.empty:
            fig_app = create_app_forecast_chart(app_forecast)
            st.plotly_chart(fig_app, use_container_width=True)
            
            # Show trend indicators
            for _, row in app_forecast.iterrows():
                trend_icon = "🔺" if row['trend'] == 'increasing' else "🔻" if row['trend'] == 'decreasing' else "➡️"
                st.caption(f"{trend_icon} **{row['app_name']}**: {row['current_avg']:.1f}h → {row['forecast_avg']:.1f}h")
    
    def _render_long_term_forecast(self, forecaster):
        """Render long-term forecast"""
        st.markdown("### 📈 Long-Term Forecast")
        
        # Preset selector
        col1, col2 = st.columns([3, 1])
        with col1:
            preset = st.selectbox(
                "Forecast Period",
                options=[1, 3, 6, 12],
                format_func=lambda x: f"Next {x} month{'s' if x > 1 else ''}",
                index=1
            )
        
        result = forecaster.forecast_long_term(months_ahead=preset)
        
        if result is None:
            st.warning("Need at least a week of data for long-term forecasting")
            return
        
        monthly_forecast, weekly_hist, stats = result
        
        # Summary metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_forecast_active = monthly_forecast['active_hours'].sum()
            st.metric(
                f"Total Active ({preset}mo)",
                f"{total_forecast_active:.0f}h",
                f"~{total_forecast_active/(preset*30):.1f}h/day"
            )
        
        with col2:
            total_forecast_break = monthly_forecast['break_hours'].sum()
            st.metric(
                f"Total Break ({preset}mo)",
                f"{total_forecast_break:.0f}h",
                f"~{total_forecast_break/(preset*30):.1f}h/day"
            )
        
        with col3:
            trend_emoji = "📈" if stats['trend_active'] == 'increasing' else "📉" if stats['trend_active'] == 'decreasing' else "➡️"
            st.metric(
                "Long-Term Trend",
                stats['trend_active'].title(),
                f"{trend_emoji}"
            )
        
        # Main forecast chart
        fig = create_long_term_forecast_chart(monthly_forecast, weekly_hist)
        st.plotly_chart(fig, use_container_width=True)
        
        # Monthly breakdown table
        st.markdown("#### 📅 Monthly Forecast Breakdown")
        display_df = monthly_forecast[['month_name', 'active_hours', 'break_hours', 'total_hours']].copy()
        display_df.columns = ['Month', 'Active Hours', 'Break Hours', 'Total Hours']
        
        st.dataframe(
            display_df.style.format({
                'Active Hours': '{:.0f}',
                'Break Hours': '{:.0f}',
                'Total Hours': '{:.0f}'
            }),
            use_container_width=True
        )
    
    def _render_insights(self, forecaster):
        """Render AI-generated insights"""
        st.markdown("---")
        st.markdown("### 💡 Insights & Recommendations")
        
        insights = forecaster.get_insights()
        
        if not insights:
            st.info("Not enough data for insights yet. Keep tracking!")
            return
        
        for insight in insights:
            if insight['type'] == 'positive':
                st.success(f"**{insight['title']}**: {insight['message']}")
            elif insight['type'] == 'warning':
                st.warning(f"**{insight['title']}**: {insight['message']}")
            else:
                st.info(f"**{insight['title']}**: {insight['message']}")
    
    def render(self):
        """Main render method"""
        self.render_header()
        self.render_sidebar()
        
        # Load data
        result = self.load_data(st.session_state.date_range)
        
        if result[0] is None:
            st.warning("🔭 No activity data found for the selected period.")
            st.info("""
**Getting Started:**
1. Ensure the Activity Watcher is running (check system tray)
2. Work for a few minutes
3. Come back here and hit Refresh

The watcher tracks your active window every 500ms automatically.
Press **Ctrl+Alt+Shift+P** to pause/resume tracking.
            """)
            return
        
        df, df_breaks, metrics_calc, metrics = result
        
        # Render all sections
        self.render_main_metrics(metrics)
        self.render_app_breakdown(metrics_calc)
        self.render_charts(df, metrics_calc, metrics)
        self.render_daily_breakdown(metrics_calc)
        
        # NEW: Forecast section
        self.render_forecast_section(df, df_breaks)
        
        # Footer
        st.markdown("---")
        st.caption("Activity Tracker | Simple • Raw • No Filters • Future Outlook")


if __name__ == "__main__":
    try:
        dashboard = ActivityDashboard()
        dashboard.render()
    except Exception as e:
        st.error(f"❌ Dashboard Error: {e}")
        logger.exception("Dashboard crashed")
        st.info("Please check the logs and ensure the database is accessible.")