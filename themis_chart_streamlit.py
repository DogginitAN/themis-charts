"""
THEMIS + TradingView Streamlit App
Interactive chart showing security mentions overlayed on TradingView price charts.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from data_fetcher import ThemisMarketDataFetcher, get_trending_symbols
from datetime import datetime, timedelta

# Page config
st.set_page_config(
    page_title="THEMIS Chart Viewer",
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
st.title("📈 THEMIS Investment Intelligence Chart Viewer")
st.markdown("View security mentions from YouTube finance channels overlayed on price charts")

# Check initialization
if not st.session_state.initialized:
    st.error(f"❌ Failed to initialize: {st.session_state.error}")
    st.info("💡 Make sure SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY environment variables are set")
    st.stop()

# Sidebar - Controls
with st.sidebar:
    st.header("⚙️ Settings")
    
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
    
    st.divider()
    
    # Symbol input
    symbol_input = st.text_input(
        "Security Symbol",
        value="AAPL",
        help="Enter stock ticker (AAPL, TSLA) or crypto (BTC, ETH, SOL)"
    ).upper()
    
    # Date range
    days_back = st.slider(
        "Days to Show",
        min_value=7,
        max_value=365,
        value=90,
        step=7
    )
    
    # Chart type
    chart_type = st.selectbox(
        "Chart Type",
        ["TradingView Widget", "Custom Interactive Chart", "Both"]
    )
    
    # Include context
    show_context = st.checkbox("Show Mention Details", value=True)
    
    # Fetch button
    fetch_button = st.button("📊 Load Chart", type="primary")

# Main content
if fetch_button or "chart_data" in st.session_state:
    
    if fetch_button:
        with st.spinner(f"Fetching data for {symbol_input}..."):
            try:
                data = st.session_state.fetcher.merge_mentions_and_prices(
                    symbol_input,
                    days_back=days_back,
                    include_context=show_context
                )
                
                if data.empty:
                    st.error(f"❌ No data found for {symbol_input}")
                    st.stop()
                
                st.session_state.chart_data = data
                st.session_state.current_symbol = symbol_input
                
            except Exception as e:
                st.error(f"❌ Error fetching data: {e}")
                st.stop()
    
    data = st.session_state.chart_data
    symbol = st.session_state.current_symbol
    
    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_mentions = int(data["mention_count"].sum())
        st.metric("Total Mentions", total_mentions)
    
    with col2:
        days_with_mentions = int((data["mention_count"] > 0).sum())
        st.metric("Days with Mentions", days_with_mentions)
    
    with col3:
        current_price = data["close"].iloc[-1]
        price_change = ((current_price - data["close"].iloc[0]) / data["close"].iloc[0]) * 100
        st.metric(
            "Price Change",
            f"{price_change:+.2f}%",
            delta=f"${current_price:.2f}"
        )
    
    with col4:
        avg_mentions = data["mention_count"].mean()
        st.metric("Avg Mentions/Day", f"{avg_mentions:.2f}")
    
    st.divider()
    
    # TradingView Widget
    if chart_type in ["TradingView Widget", "Both"]:
        st.subheader(f"📈 {symbol} - TradingView Chart")
        
        # Determine TradingView symbol format
        if symbol in ["BTC", "ETH", "SOL", "ADA", "DOGE", "XRP", "AVAX", "MATIC"]:
            tv_symbol = f"COINBASE:{symbol}USD"
        else:
            tv_symbol = f"NASDAQ:{symbol}"
        
        # TradingView widget HTML
        tradingview_html = f"""
        <div class="tradingview-widget-container" style="height:600px">
          <div id="tradingview_chart" style="height:100%"></div>
          <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
          <script type="text/javascript">
            new TradingView.widget({{
              "width": "100%",
              "height": 600,
              "symbol": "{tv_symbol}",
              "interval": "D",
              "timezone": "Etc/UTC",
              "theme": "dark",
              "style": "1",
              "locale": "en",
              "toolbar_bg": "#f1f3f6",
              "enable_publishing": false,
              "allow_symbol_change": true,
              "container_id": "tradingview_chart",
              "studies": [
                "MASimple@tv-basicstudies",
                "RSI@tv-basicstudies"
              ],
              "save_image": true,
              "show_popup_button": true
            }});
          </script>
        </div>
        """
        
        st.components.v1.html(tradingview_html, height=620)
        
        st.info("💡 The TradingView widget above shows live price data with technical indicators. Mention markers cannot be added to the free widget.")
    
    # Custom Interactive Chart with Mentions
    if chart_type in ["Custom Interactive Chart", "Both"]:
        st.subheader(f"📊 {symbol} - Price Action with THEMIS Mentions")
        
        # Create subplot with secondary y-axis
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            subplot_titles=(f'{symbol} Price', 'Mention Frequency'),
            row_heights=[0.7, 0.3],
            specs=[[{"secondary_y": False}],
                   [{"secondary_y": False}]]
        )
        
        # Candlestick chart
        fig.add_trace(
            go.Candlestick(
                x=data['date'],
                open=data['open'],
                high=data['high'],
                low=data['low'],
                close=data['close'],
                name='Price',
                increasing_line_color='#26a69a',
                decreasing_line_color='#ef5350'
            ),
            row=1, col=1
        )
        
        # Add mention markers on price chart
        mention_dates = data[data['mention_count'] > 0]
        if not mention_dates.empty:
            fig.add_trace(
                go.Scatter(
                    x=mention_dates['date'],
                    y=mention_dates['high'] * 1.02,  # Slightly above high
                    mode='markers',
                    marker=dict(
                        symbol='triangle-down',
                        size=mention_dates['mention_count'] * 3 + 5,  # Size based on count
                        color='#2196F3',
                        line=dict(color='white', width=1)
                    ),
                    name='Mentions',
                    text=mention_dates['mention_count'],
                    hovertemplate='<b>%{x}</b><br>Mentions: %{text}<extra></extra>'
                ),
                row=1, col=1
            )
        
        # Mention frequency bar chart
        fig.add_trace(
            go.Bar(
                x=data['date'],
                y=data['mention_count'],
                name='Mention Count',
                marker_color='#2196F3',
                hovertemplate='<b>%{x}</b><br>Mentions: %{y}<extra></extra>'
            ),
            row=2, col=1
        )
        
        # Update layout
        fig.update_layout(
            height=700,
            showlegend=True,
            hovermode='x unified',
            xaxis_rangeslider_visible=False,
            template='plotly_dark',
            margin=dict(l=50, r=50, t=50, b=50)
        )
        
        fig.update_xaxes(title_text="Date", row=2, col=1)
        fig.update_yaxes(title_text="Price ($)", row=1, col=1)
        fig.update_yaxes(title_text="Mentions", row=2, col=1)
        
        st.plotly_chart(fig, use_container_width=True)
        
        st.info("💡 Blue triangles indicate days with YouTube mentions. Triangle size = mention count.")
    
    # Mention details table
    if show_context and "video_title" in data.columns:
        st.subheader("📝 Mention Details")
        
        mention_details = data[data["mention_count"] > 0].copy()
        
        if not mention_details.empty:
            # Expand context fields
            mention_details["channels"] = mention_details["channel_name"].apply(
                lambda x: ", ".join(x) if isinstance(x, list) else str(x)
            )
            mention_details["videos"] = mention_details["video_title"].apply(
                lambda x: ", ".join(x[:3]) if isinstance(x, list) else str(x)  # Limit to 3 videos
            )
            
            display_df = mention_details[[
                "date", "mention_count", "close", "channels", "videos"
            ]].sort_values("date", ascending=False)
            
            display_df.columns = ["Date", "Mentions", "Price ($)", "Channels", "Video Titles"]
            
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True
            )
            
            # Download button
            csv = display_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Mention Data (CSV)",
                data=csv,
                file_name=f"themis_{symbol}_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
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
    
    1. **Select a Symbol** - Enter any stock ticker (AAPL, TSLA) or crypto (BTC, ETH, SOL)
    2. **Load Chart** - Fetches THEMIS mentions + historical price data
    3. **Analyze** - See when the security was mentioned on YouTube finance channels
    4. **Correlate** - Identify if mentions preceded price movements
    
    ### 📊 Chart Features
    
    - **TradingView Widget**: Full-featured chart with technical indicators (MA, RSI)
    - **Custom Chart**: Interactive price chart with mention markers
    - **Mention Timeline**: Bar chart showing mention frequency over time
    - **Context Details**: See which channels/videos mentioned the security
    
    ### 💡 Use Cases
    
    - **Signal Detection**: Identify securities gaining attention
    - **Timing Analysis**: Correlate mentions with price action
    - **Source Verification**: See which channels are discussing a security
    - **Trend Validation**: Cross-reference buzz with technical indicators
    """)

# Footer
st.divider()
st.caption("📊 THEMIS Investment Intelligence Platform | Data from YouTube Finance Channels + Market APIs")
