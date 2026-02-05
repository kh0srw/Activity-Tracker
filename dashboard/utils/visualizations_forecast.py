"""
Forecast Visualizations
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd

def create_short_term_forecast_chart(forecast_df, historical_df):
    """Create short-term forecast chart (days/weeks)"""
    fig = go.Figure()
    
    # Historical data
    fig.add_trace(go.Scatter(
        x=historical_df['date'],
        y=historical_df['active_hours'],
        name='Historical Active',
        mode='lines+markers',
        line=dict(color='#10B981', width=2),
        marker=dict(size=6)
    ))
    
    # Forecast data
    fig.add_trace(go.Scatter(
        x=forecast_df['date'],
        y=forecast_df['active_hours'],
        name='Forecast Active',
        mode='lines+markers',
        line=dict(color='#10B981', width=2, dash='dash'),
        marker=dict(size=6, symbol='diamond')
    ))
    
    # Add break time
    fig.add_trace(go.Scatter(
        x=historical_df['date'],
        y=historical_df['break_hours'],
        name='Historical Break',
        mode='lines+markers',
        line=dict(color='#F59E0B', width=2),
        marker=dict(size=6)
    ))
    
    fig.add_trace(go.Scatter(
        x=forecast_df['date'],
        y=forecast_df['break_hours'],
        name='Forecast Break',
        mode='lines+markers',
        line=dict(color='#F59E0B', width=2, dash='dash'),
        marker=dict(size=6, symbol='diamond')
    ))
    
    # Add vertical line to separate historical from forecast
    if len(historical_df) > 0:
        last_date = historical_df['date'].max()
        # FIX: Convert date to numeric timestamp (milliseconds) to avoid Plotly TypeError
        # Plotly's internal sum() fails on datetime.date objects (0 + date)
        x_location = pd.Timestamp(last_date).timestamp() * 1000
        
        fig.add_vline(
            x=x_location,
            line_dash="dot",
            line_color="gray",
            annotation_text="Forecast Start",
            annotation_position="top"
        )
    
    fig.update_layout(
        title='Short-Term Activity Forecast',
        xaxis_title='Date',
        yaxis_title='Hours',
        hovermode='x unified',
        template='plotly_white',
        height=400
    )
    
    return fig


def create_long_term_forecast_chart(monthly_forecast, weekly_historical):
    """Create long-term forecast chart (months)"""
    fig = go.Figure()
    
    # Historical weekly data aggregated to monthly
    if not weekly_historical.empty:
        weekly_historical = weekly_historical.copy()
        weekly_historical['month'] = weekly_historical['week'].apply(lambda x: x.start_time.to_period('M'))
        monthly_hist = weekly_historical.groupby('month').agg({
            'active_hours': 'sum',
            'break_hours': 'sum'
        }).reset_index()
        
        monthly_hist['month_name'] = monthly_hist['month'].apply(lambda x: x.strftime('%B %Y'))
        
        fig.add_trace(go.Bar(
            x=monthly_hist['month_name'],
            y=monthly_hist['active_hours'],
            name='Historical Active',
            marker_color='#10B981',
            opacity=0.8
        ))
        
        fig.add_trace(go.Bar(
            x=monthly_hist['month_name'],
            y=monthly_hist['break_hours'],
            name='Historical Break',
            marker_color='#F59E0B',
            opacity=0.8
        ))
    
    # Forecast data
    fig.add_trace(go.Bar(
        x=monthly_forecast['month_name'],
        y=monthly_forecast['active_hours'],
        name='Forecast Active',
        marker_color='#10B981',
        opacity=0.4,
        marker_pattern_shape="/"
    ))
    
    fig.add_trace(go.Bar(
        x=monthly_forecast['month_name'],
        y=monthly_forecast['break_hours'],
        name='Forecast Break',
        marker_color='#F59E0B',
        opacity=0.4,
        marker_pattern_shape="/"
    ))
    
    fig.update_layout(
        title='Long-Term Activity Forecast (Monthly)',
        xaxis_title='Month',
        yaxis_title='Hours',
        barmode='stack',
        template='plotly_white',
        height=400
    )
    
    return fig


def create_trend_comparison_chart(forecast_df, historical_df, metric='active_hours', title='Activity Trend'):
    """Create a comparison chart showing trend line"""
    fig = go.Figure()
    
    # Historical data points
    fig.add_trace(go.Scatter(
        x=list(range(len(historical_df))),
        y=historical_df[metric],
        name='Actual',
        mode='markers',
        marker=dict(size=8, color='#3B82F6')
    ))
    
    # Trend line through historical
    x_hist = list(range(len(historical_df)))
    fig.add_trace(go.Scatter(
        x=x_hist,
        y=historical_df[metric],
        name='Historical Trend',
        mode='lines',
        line=dict(color='#3B82F6', width=2),
        showlegend=False
    ))
    
    # Forecast trend
    x_forecast = list(range(len(historical_df), len(historical_df) + len(forecast_df)))
    fig.add_trace(go.Scatter(
        x=x_forecast,
        y=forecast_df[metric],
        name='Forecast',
        mode='lines+markers',
        line=dict(color='#3B82F6', width=2, dash='dash'),
        marker=dict(size=8, symbol='diamond')
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title='Days',
        yaxis_title='Hours',
        template='plotly_white',
        height=300
    )
    
    return fig


def create_app_forecast_chart(app_forecast_df):
    """Create chart showing forecast for top apps"""
    if app_forecast_df is None or app_forecast_df.empty:
        return go.Figure()
    
    fig = go.Figure()
    
    # Current vs forecast
    x_pos = list(range(len(app_forecast_df)))
    
    fig.add_trace(go.Bar(
        x=x_pos,
        y=app_forecast_df['current_avg'],
        name='Current Avg',
        marker_color='#6366F1',
        text=app_forecast_df['app_name'],
        textposition='outside'
    ))
    
    fig.add_trace(go.Bar(
        x=x_pos,
        y=app_forecast_df['forecast_avg'],
        name='Forecast Avg',
        marker_color='#8B5CF6',
        opacity=0.6
    ))
    
    fig.update_layout(
        title='Application Usage Forecast',
        xaxis_title='Application',
        yaxis_title='Hours/Day',
        barmode='group',
        template='plotly_white',
        height=350,
        xaxis=dict(tickmode='array', tickvals=x_pos, ticktext=app_forecast_df['app_name'])
    )
    
    return fig


def create_forecast_gauge(current_value, forecast_value, title='Activity Level'):
    """Create gauge showing current vs forecast"""
    change_pct = ((forecast_value - current_value) / current_value * 100) if current_value > 0 else 0
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=forecast_value,
        delta={'reference': current_value, 'relative': False, 'suffix': 'h'},
        title={'text': title},
        gauge={
            'axis': {'range': [0, max(current_value, forecast_value) * 1.5]},
            'bar': {'color': "#10B981" if forecast_value >= current_value else "#EF4444"},
            'steps': [
                {'range': [0, current_value], 'color': "lightgray"},
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': current_value
            }
        }
    ))
    
    fig.update_layout(
        height=250,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    return fig


def create_projection_summary(stats_dict):
    """Create a summary card figure"""
    fig = go.Figure()
    
    # Create text summary
    trend_active = stats_dict.get('trend_active', 'stable')
    trend_break = stats_dict.get('trend_break', 'stable')
    
    trend_colors = {
        'increasing': '🔺 Increasing',
        'decreasing': '🔻 Decreasing',
        'stable': '➡️ Stable'
    }
    
    summary_text = f"""
    <b>Activity Trend:</b> {trend_colors.get(trend_active, trend_active)}<br>
    <b>Break Trend:</b> {trend_colors.get(trend_break, trend_break)}<br>
    <b>Average Active:</b> {stats_dict.get('avg_active', 0):.1f}h/day<br>
    <b>Average Break:</b> {stats_dict.get('avg_break', 0):.1f}h/day
    """
    
    fig.add_annotation(
        text=summary_text,
        xref="paper", yref="paper",
        x=0.5, y=0.5,
        showarrow=False,
        font=dict(size=14),
        align='left'
    )
    
    fig.update_layout(
        height=200,
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(showgrid=False, showticklabels=False, zeroline=False)
    )
    
    return fig
