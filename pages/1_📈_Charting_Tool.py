"""
THEMIS Charting Tool - TradingView Integration
Interactive chart showing security mentions overlayed on TradingView price charts.
Features: Toggle for inferred mentions + visual distinction between mentioned/inferred.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys

from data_fetcher import ThemisMarketDataFetcher, get_trending_symbols
from datetime import datetime, timedelta

# Page config
st.set_page_config(
    page_title="THEMIS Charting Tool",
    page_icon="📈",
    layout="wide"
)

# Initialize session state
if "fetcher" not in st.session_state:
    try:
        st.session_state.fetcher = ThemisMarketDataFetcher()
        st.session_state.initialized = True
    except Exception as e:
        st.session_state.initialized = False
        st.session_state.error = str(e)

# Title
st.title("📈 THEMIS Charting Tool")
st.markdown("View security mentions from YouTube finance channels overlayed on price charts")  # v2.0 - Button Navigation

# Check initialization
if not st.session_state.initialized:
    st.error(f"❌ Failed to initialize: {st.session_state.error}")
    st.info("💡 Make sure THEMIS_ANALYST_DB or SUPABASE_DB environment variable is set")
    st.stop()

# Sidebar - Controls
with st.sidebar:
    st.header("⚙️ Settings")
    
    # Symbol input
    symbol_input = st.text_input(
        "Security Symbol",
        value="AAPL",
        help="Enter stock ticker (AAPL, TSLA) or crypto (BTC, ETH, SOL)"
    ).upper()
    
    # Date range buttons
    st.markdown("**Time Range**")
    cols = st.columns(5)
    
    date_options = {
        "30D": 30,
        "90D": 90,
        "6M": 180,
        "1Y": 365,
        "5Y": 1825
    }
    
    # Initialize session state for selected range
    if "selected_range" not in st.session_state:
        st.session_state.selected_range = 365  # Default to 1Y
    
    for idx, (label, days) in enumerate(date_options.items()):
        with cols[idx]:
            if st.button(
                label, 
                key=f"range_{label}",
                use_container_width=True,
                type="primary" if st.session_state.selected_range == days else "secondary"
            ):
                st.session_state.selected_range = days
    
    days_back = st.session_state.selected_range
    
    # Chart type
    chart_type = st.selectbox(
        "Chart Type",
        ["Custom Interactive Chart", "TradingView Widget", "Both"]
    )
    
    # Include inferred toggle
    include_inferred = st.checkbox(
        "Include Inferred Mentions",
        value=True,
        help="Inferred = LLM identified relevant security from context. Mentioned = Explicitly named by creator."
    )
    
    # Include context
    show_context = st.checkbox("Show Mention Details", value=True)
    
    # Fetch button
    fetch_button = st.button("📊 Load Chart", type="primary")
    
    st.divider()
    
    # Show trending securities
    st.subheader("🔥 Trending (Last 7 Days)")
    try:
        trending = st.session_state.fetcher.get_trending_securities(days=7, limit=10)
        if trending:
            for sec in trending:
                st.metric(
                    label=f"{sec['security_symbol']} ({sec['security_type']})",
                    value=f"{sec['mention_count']} mentions"
                )
        else:
            st.info("No recent mentions found")
    except Exception as e:
        st.warning(f"Could not fetch trending: {e}")

# Main content
if fetch_button or "chart_data" in st.session_state:
    
    if fetch_button:
        with st.spinner(f"Fetching data for {symbol_input}..."):
            try:
                data = st.session_state.fetcher.merge_mentions_and_prices(
                    symbol_input,
                    days_back=days_back,
                    include_context=show_context,
                    include_inferred=include_inferred
                )
                
                if data.empty:
                    st.error(f"❌ No data found for {symbol_input}")
                    st.stop()
                
                st.session_state.chart_data = data
                st.session_state.current_symbol = symbol_input
                st.session_state.include_inferred = include_inferred
                
            except Exception as e:
                st.error(f"❌ Error fetching data: {e}")
                import traceback
                st.error(traceback.format_exc())
                st.stop()
    
    data = st.session_state.chart_data
    symbol = st.session_state.current_symbol
    
    # Calculate enhanced metrics
    total_mentions = int(data["mention_count"].sum())
    mentioned_count = int(data.get("mentioned_count", pd.Series(0)).sum())
    inferred_count = int(data.get("inferred_count", pd.Series(0)).sum())
    days_with_mentions = int((data["mention_count"] > 0).sum())
    
    # Price change from first mention
    if total_mentions > 0:
        first_mention_idx = data[data["mention_count"] > 0].index[0]
        first_mention_price = data.loc[first_mention_idx, "close"]
        current_price = data["close"].iloc[-1]
        price_change_from_mention = ((current_price - first_mention_price) / first_mention_price) * 100
    else:
        first_mention_price = None
        current_price = data["close"].iloc[-1]
        price_change_from_mention = 0
    
    # Correlation coefficient
    data['returns'] = data['close'].pct_change()
    
    if total_mentions > 0 and len(data) > 1:
        correlation = data['mention_count'].corr(data['returns'])
        data['next_day_returns'] = data['returns'].shift(-1)
        lagged_correlation = data['mention_count'].corr(data['next_day_returns'])
    else:
        correlation = 0
        lagged_correlation = 0
    
    # Metrics row 1
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if mentioned_count > 0 and inferred_count > 0:
            st.metric("Total Mentions", total_mentions, delta=f"{mentioned_count} explicit, {inferred_count} inferred")
        else:
            st.metric("Total Mentions", total_mentions)
    
    with col2:
        st.metric("Days with Mentions", days_with_mentions)
    
    with col3:
        if first_mention_price:
            st.metric(
                "Price Change Since First Mention",
                f"{price_change_from_mention:+.2f}%",
                delta=f"${current_price:.2f}",
                help=f"Price change from first mention ({data.loc[first_mention_idx, 'date']}) to now"
            )
        else:
            st.metric(
                "Price Change (Period)",
                f"{((current_price - data['close'].iloc[0]) / data['close'].iloc[0]) * 100:+.2f}%",
                delta=f"${current_price:.2f}",
                help="No mentions in this period - showing total period change"
            )
    
    with col4:
        avg_mentions = data["mention_count"].mean()
        st.metric("Avg Mentions/Day", f"{avg_mentions:.2f}")
    
    # Metrics row 2
    col5, col6, col7, col8 = st.columns(4)
    
    with col5:
        corr_label = "Strong" if abs(correlation) >= 0.3 else "Moderate" if abs(correlation) >= 0.1 else "Weak"
        st.metric("Mention-Price Correlation", f"{correlation:.3f}", delta=corr_label,
                 help="Correlation between mention count and same-day returns")
    
    with col6:
        st.metric("Next-Day Correlation", f"{lagged_correlation:.3f}",
                 help="Predictive signal - mentions today vs price tomorrow")
    
    with col7:
        if total_mentions > 0:
            mention_days = data[data["mention_count"] > 0]
            avg_return = mention_days["returns"].mean() * 100
            st.metric("Avg Return on Mention Days", f"{avg_return:+.2f}%")
        else:
            st.metric("Avg Return on Mention Days", "N/A")
    
    with col8:
        volatility = data["returns"].std() * np.sqrt(252) * 100
        st.metric("Volatility (Annual)", f"{volatility:.1f}%")
    
    st.divider()
    
    # CUSTOM INTERACTIVE CHART
    if chart_type in ["Custom Interactive Chart", "Both"]:
        st.subheader(f"📊 {symbol} - Price Action with THEMIS Mentions")
        
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            subplot_titles=(f'{symbol} Price', 'Mention Frequency'),
            row_heights=[0.7, 0.3],
            specs=[[{"secondary_y": False}], [{"secondary_y": False}]]
        )
        
        # Candlestick
        fig.add_trace(
            go.Candlestick(
                x=data['date'], open=data['open'], high=data['high'],
                low=data['low'], close=data['close'], name='Price',
                increasing_line_color='#26a69a', decreasing_line_color='#ef5350'
            ), row=1, col=1
        )
        
        # Mention markers by type
        if "mentioned_count" in data.columns and "inferred_count" in data.columns:
            # Explicit mentions
            mentioned_dates = data[data['mentioned_count'] > 0]
            if not mentioned_dates.empty:
                fig.add_trace(
                    go.Scatter(
                        x=mentioned_dates['date'], y=mentioned_dates['high'] * 1.02,
                        mode='markers',
                        marker=dict(symbol='triangle-down', size=mentioned_dates['mentioned_count'] * 3 + 5,
                                   color='#2196F3', line=dict(color='white', width=1)),
                        name='Explicit Mentions', text=mentioned_dates['mentioned_count'],
                        hovertemplate='<b>%{x}</b><br>Explicit: %{text}<extra></extra>'
                    ), row=1, col=1
                )
            
            # Inferred mentions
            inferred_dates = data[data['inferred_count'] > 0]
            if not inferred_dates.empty:
                fig.add_trace(
                    go.Scatter(
                        x=inferred_dates['date'], y=inferred_dates['high'] * 1.04,
                        mode='markers',
                        marker=dict(symbol='circle', size=inferred_dates['inferred_count'] * 2 + 5,
                                   color='#FFC107', line=dict(color='white', width=1)),
                        name='Inferred Mentions', text=inferred_dates['inferred_count'],
                        hovertemplate='<b>%{x}</b><br>Inferred: %{text}<extra></extra>'
                    ), row=1, col=1
                )
            
            # Stacked bar chart
            fig.add_trace(go.Bar(x=data['date'], y=data['mentioned_count'], name='Explicit',
                                marker_color='#2196F3'), row=2, col=1)
            fig.add_trace(go.Bar(x=data['date'], y=data['inferred_count'], name='Inferred',
                                marker_color='#FFC107'), row=2, col=1)
            fig.update_layout(barmode='stack')
        else:
            # Single marker type fallback
            mention_dates = data[data['mention_count'] > 0]
            if not mention_dates.empty:
                fig.add_trace(
                    go.Scatter(
                        x=mention_dates['date'], y=mention_dates['high'] * 1.02,
                        mode='markers',
                        marker=dict(symbol='triangle-down', size=mention_dates['mention_count'] * 3 + 5,
                                   color='#2196F3', line=dict(color='white', width=1)),
                        name='Mentions', text=mention_dates['mention_count'],
                        hovertemplate='<b>%{x}</b><br>Mentions: %{text}<extra></extra>'
                    ), row=1, col=1
                )
            fig.add_trace(go.Bar(x=data['date'], y=data['mention_count'], name='Mentions',
                                marker_color='#2196F3'), row=2, col=1)
        
        fig.update_layout(height=700, showlegend=True, hovermode='x unified',
                         xaxis_rangeslider_visible=False, template='plotly_dark',
                         margin=dict(l=50, r=50, t=50, b=50))
        fig.update_xaxes(title_text="Date", row=2, col=1)
        fig.update_yaxes(title_text="Price ($)", row=1, col=1)
        fig.update_yaxes(title_text="Mentions", row=2, col=1)
        
        st.plotly_chart(fig, use_container_width=True)
        st.info("💡 🔵 Blue triangles = Explicit mentions | 🟡 Yellow circles = Inferred mentions")
    
    # TradingView Widget
    if chart_type in ["TradingView Widget", "Both"]:
        st.subheader(f"📈 {symbol} - TradingView Chart")
        
        tv_symbol = f"COINBASE:{symbol}USD" if symbol in ["BTC", "ETH", "SOL", "ADA", "DOGE", "XRP", "AVAX", "MATIC"] else f"NASDAQ:{symbol}"
        
        tradingview_html = f"""
        <div class="tradingview-widget-container" style="height:600px">
          <div id="tradingview_chart" style="height:100%"></div>
          <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
          <script type="text/javascript">
            new TradingView.widget({{
              "width": "100%", "height": 600, "symbol": "{tv_symbol}", "interval": "D",
              "timezone": "Etc/UTC", "theme": "dark", "style": "1", "locale": "en",
              "toolbar_bg": "#f1f3f6", "enable_publishing": false, "allow_symbol_change": true,
              "container_id": "tradingview_chart",
              "studies": ["MASimple@tv-basicstudies", "RSI@tv-basicstudies"],
              "save_image": true, "show_popup_button": true
            }});
          </script>
        </div>
        """
        st.components.v1.html(tradingview_html, height=620)
        st.info("💡 TradingView widget shows live price data with technical indicators")
    
    # Mention details table
    if show_context and "theme_name" in data.columns:
        st.subheader("📝 Mention Details")
        mention_details = data[data["mention_count"] > 0].copy()
        
        if not mention_details.empty:
            display_columns = ["date", "mention_count", "close"]
            column_names = ["Date", "Total Mentions", "Price ($)"]
            
            if "mentioned_count" in mention_details.columns:
                display_columns.append("mentioned_count")
                column_names.append("Explicit")
            if "inferred_count" in mention_details.columns:
                display_columns.append("inferred_count")
                column_names.append("Inferred")
            if "channel_name" in mention_details.columns:
                mention_details["channels"] = mention_details["channel_name"].apply(
                    lambda x: ", ".join(x) if isinstance(x, list) else str(x))
                display_columns.append("channels")
                column_names.append("Channels")
            if "theme_name" in mention_details.columns:
                mention_details["themes"] = mention_details["theme_name"].apply(
                    lambda x: ", ".join(x[:3]) if isinstance(x, list) else str(x))
                display_columns.append("themes")
                column_names.append("Themes")
            if "video_title" in mention_details.columns:
                mention_details["videos"] = mention_details["video_title"].apply(
                    lambda x: ", ".join(x[:2]) if isinstance(x, list) else str(x))
                display_columns.append("videos")
                column_names.append("Video Titles")
            
            display_df = mention_details[display_columns].sort_values("date", ascending=False)
            display_df.columns = column_names
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            csv = display_df.to_csv(index=False)
            st.download_button("📥 Download Mention Data (CSV)", csv,
                             f"themis_{symbol}_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv")
        else:
            st.info(f"No mentions found for {symbol} in the selected time period")
    
    # Raw data expander
    with st.expander("🔍 View Raw Data"):
        st.dataframe(data, use_container_width=True)

else:
    # Welcome screen
    st.info("👈 Select a security symbol in the sidebar and click 'Load Chart' to begin")
    
    st.markdown("""
    ### 🎯 How It Works
    
    1. **Select a Symbol** - Enter any stock ticker or crypto
    2. **Load Chart** - Fetches THEMIS mentions + historical price data
    3. **Analyze** - See when mentioned on YouTube finance channels
    4. **Correlate** - Identify if mentions preceded price movements
    
    ### 🎨 Features
    
    - 🔵 **Blue Triangles** = Explicit mentions (creator named it directly)
    - 🟡 **Yellow Circles** = Inferred mentions (AI identified from context)
    - 📊 Correlation metrics & statistical analysis
    - 📥 CSV export for further research
    """)

st.divider()
st.caption("📊 THEMIS Investment Intelligence Platform")
