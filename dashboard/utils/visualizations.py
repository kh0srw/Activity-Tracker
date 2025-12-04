"""
Visualization Utilities - Simplified
Only: Time allocation, App breakdown, Daily trend
"""
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import config


def create_time_pie(metrics):
    """Create simple pie chart for active vs break time"""
    data = pd.DataFrame({
        'Category': ['Active Time', 'Break Time'],
        'Minutes': [
            metrics['total_active_min'],
            metrics['total_break_min']
        ]
    })
    
    # Filter out zero values
    data = data[data['Minutes'] > 0]
    
    if data.empty:
        return go.Figure()
    
    colors = [config.COLOR_ACTIVE, config.COLOR_BREAK]
    
    fig = px.pie(
        data,
        values='Minutes',
        names='Category',
        title='Active vs Break Time',
        color_discrete_sequence=colors[:len(data)],
        hole=0.4
    )
    
    fig.update_traces(
        textposition='inside',
        textinfo='percent+label',
        hovertemplate='<b>%{label}</b><br>%{value:.0f} min<br>%{percent}<extra></extra>'
    )
    
    fig.update_layout(height=config.CHART_HEIGHT)
    
    return fig


def create_daily_trend(metrics_calc):
    """Create daily trend bar chart"""
    daily = metrics_calc.get_daily_breakdown()
    
    if daily.empty:
        return go.Figure()
    
    daily_reset = daily.reset_index()
    
    fig = go.Figure()
    
    # Active time bars
    fig.add_trace(go.Bar(
        x=daily_reset['date'],
        y=daily_reset['active_min'],
        name='Active Time',
        marker_color=config.COLOR_ACTIVE,
        hovertemplate='%{y:.0f} min<extra></extra>'
    ))
    
    # Break time bars
    if 'break_min' in daily_reset.columns:
        fig.add_trace(go.Bar(
            x=daily_reset['date'],
            y=daily_reset['break_min'],
            name='Break Time',
            marker_color=config.COLOR_BREAK,
            hovertemplate='%{y:.0f} min<extra></extra>'
        ))
    
    fig.update_layout(
        title='Daily Activity Trend',
        xaxis_title='Date',
        yaxis_title='Minutes',
        barmode='stack',
        height=config.CHART_HEIGHT,
        hovermode='x unified',
        showlegend=True,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
    )
    
    return fig


def create_hourly_heatmap(df):
    """Create heatmap of hourly activity"""
    df['day_of_week'] = df['timestamp_dt'].dt.day_name()
    
    heatmap_data = df.groupby(['day_of_week', 'hour'])['duration_min'].sum().unstack(fill_value=0)
    
    # Reorder days
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    heatmap_data = heatmap_data.reindex([d for d in day_order if d in heatmap_data.index])
    
    if heatmap_data.empty:
        return go.Figure()
    
    fig = go.Figure(data=go.Heatmap(
        z=heatmap_data.values,
        x=heatmap_data.columns,
        y=heatmap_data.index,
        colorscale='Viridis',
        hovertemplate='Hour: %{x}<br>Day: %{y}<br>Activity: %{z:.0f} min<extra></extra>'
    ))
    
    fig.update_layout(
        title='Activity Heatmap (by Hour and Day)',
        xaxis_title='Hour of Day',
        yaxis_title='Day of Week',
        height=400
    )
    
    return fig


def create_app_breakdown_chart(app_stats, top_n=15):
    """Create horizontal bar chart of top applications by time"""
    if app_stats.empty:
        return go.Figure()
    
    top_apps = app_stats.head(top_n).sort_values('duration_min')
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        y=top_apps.index,
        x=top_apps['duration_min'],
        orientation='h',
        marker_color=config.COLOR_ACTIVE,
        text=top_apps.apply(
            lambda row: f"{row['duration_min']:.0f} min ({row['percentage']:.1f}%)",
            axis=1
        ),
        textposition='outside',
        hovertemplate='<b>%{y}</b><br>Time: %{x:.0f} min<extra></extra>',
    ))
    
    fig.update_layout(
        title=f'Top {min(top_n, len(top_apps))} Applications by Time',
        xaxis_title='Minutes',
        yaxis_title='Application',
        height=max(400, len(top_apps) * 30),  # Dynamic height
        showlegend=False,
        margin=dict(l=150)  # More space for app names
    )
    
    return fig


def create_app_pie_chart(app_stats, top_n=10):
    """Create pie chart of top applications"""
    if app_stats.empty:
        return go.Figure()
    
    top_apps = app_stats.head(top_n).copy()
    
    # Group remaining apps as "Other"
    if len(app_stats) > top_n:
        other_min = app_stats.iloc[top_n:]['duration_min'].sum()
        other_row = pd.DataFrame({
            'duration_min': [other_min],
            'percentage': [other_min / app_stats['duration_min'].sum() * 100]
        }, index=['Other'])
        top_apps = pd.concat([top_apps, other_row])
    
    fig = px.pie(
        top_apps.reset_index(),
        values='duration_min',
        names='app_name' if 'app_name' in top_apps.reset_index().columns else 'index',
        title=f'Time Distribution by Application',
        hole=0.3
    )
    
    fig.update_traces(
        textposition='inside',
        textinfo='percent+label',
        hovertemplate='<b>%{label}</b><br>%{value:.0f} min<br>%{percent}<extra></extra>'
    )
    
    fig.update_layout(height=config.CHART_HEIGHT)
    
    return fig
