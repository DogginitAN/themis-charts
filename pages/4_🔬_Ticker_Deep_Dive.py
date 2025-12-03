"""
THEMIS Ticker Deep Dive - Individual Signal Inspector
Detailed validation and analysis of individual tickers with confluence narrative.
"""

import streamlit as st
import pandas as pd
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import plotly.graph_objects as go
from datetime import datetime, timedelta
import yfinance as yf

# Page config
st.set_page_config(
    page_title="Ticker Deep Dive - THEMIS",
    page_icon="🔬",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    .main {
        font-family: 'Inter', sans-serif;
    }
    
    /* Info cards */
    .info-card {
        background: linear-gradient(135deg, #1a1d24 0%, #262730 100%);
        border: 2px solid #3d4858;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
    }
    
    .info-card h3 {
        color: #FF6B35;
        margin-top: 0;
        font-size: 1.2rem;
    }
    
    .info-card p {
        color: #E8E9ED;
        line-height: 1.6;
    }
    
    /* Metric boxes */
    .metric-box {
        background: linear-gradient(135deg, #2d1b4e 0%, #1a1d24 100%);
        border: 2px solid #4a3a6a;
        border-radius: 10px;
        padding: 1.2rem;
        text-align: center;
        margin-bottom: 1rem;
    }
    
    .metric-box-value {
        font-size: 2rem;
        font-weight: 700;
        color: #FF6B35;
    }
    
    .metric-box-label {
        font-size: 0.9rem;
        color: #B8BCC8;
        text-transform: uppercase;
        margin-top: 0.5rem;
    }
    
    .metric-box-sublabel {
        font-size: 0.75rem;
        color: #7B8794;
        margin-top: 0.25rem;
    }
</style>
""", unsafe_allow_html=True)

# Database connection
DB_CONNECTION = os.getenv("THEMIS_ANALYST_DB") or os.getenv("SUPABASE_DB")

@st.cache_data(ttl=300)
def fetch_available_tickers():
    """Fetch all tickers with confluence data."""
    conn = psycopg2.connect(DB_CONNECTION)
    
    query = """
    SELECT DISTINCT ticker 
    FROM confluence_metrics 
    ORDER BY ticker
    """
    
    try:
        df = pd.read_sql_query(query, conn)
        return df['ticker'].tolist()
    finally:
        conn.close()

@st.cache_data(ttl=3600)  # Cache for 1 hour - total channels doesn't change often
def get_total_channels():
    """Get total number of channels in the database."""
    conn = psycopg2.connect(DB_CONNECTION)
    
    query = "SELECT COUNT(DISTINCT id) as total FROM channels"
    
    try:
        df = pd.read_sql_query(query, conn)
        return int(df['total'].iloc[0]) if not df.empty else 15  # Fallback to 15
    finally:
        conn.close()

@st.cache_data(ttl=300)
def fetch_ticker_details(ticker):
    """Fetch complete ticker details including confluence, market data, and signals."""
    conn = psycopg2.connect(DB_CONNECTION, cursor_factory=RealDictCursor)
    
    try:
        with conn.cursor() as cur:
            # Get confluence metrics
            cur.execute("""
                SELECT * FROM confluence_metrics 
                WHERE ticker = %s 
                ORDER BY date DESC 
                LIMIT 1
            """, (ticker,))
            confluence = cur.fetchone()
            
            # Get market data
            cur.execute("""
                SELECT * FROM market_data 
                WHERE ticker = %s 
                ORDER BY date DESC 
                LIMIT 1
            """, (ticker,))
            market_data = cur.fetchone()
            
            # Get active signal
            cur.execute("""
                SELECT * FROM conviction_signals 
                WHERE ticker = %s AND is_active = TRUE
                ORDER BY date DESC 
                LIMIT 1
            """, (ticker,))
            signal = cur.fetchone()
            
            # Convert to dicts
            confluence_dict = dict(confluence) if confluence else None
            market_data_dict = dict(market_data) if market_data else None
            signal_dict = dict(signal) if signal else None
            
            # TASK 1: Fix Channel Diversity Score (DYNAMIC)
            if confluence_dict and confluence_dict.get('channel_diversity_score', 0) == 0:
                unique_channels = confluence_dict.get('unique_channels', 0)
                if unique_channels > 0:
                    # Get total channels dynamically
                    total_channels = get_total_channels()
                    # Normalize against actual total
                    raw_score = (unique_channels / total_channels) * 100
                    confluence_dict['channel_diversity_score'] = min(raw_score, 100.0)
            
    finally:
        conn.close()
    
    # TASK 2: Fetch price history from yfinance (not database)
    price_history = []
    try:
        ticker_obj = yf.Ticker(ticker)
        hist = ticker_obj.history(period="1y")  # 6 months for better SMA context
        
        if not hist.empty:
            hist = hist.reset_index()
            hist['date'] = pd.to_datetime(hist['Date']).dt.date
            hist['close'] = hist['Close']
            
            # Calculate SMAs manually to ensure they exist
            hist['sma_50'] = hist['Close'].rolling(window=50).mean()
            hist['sma_200'] = hist['Close'].rolling(window=200).mean()
            
            # Convert to list of dicts
            price_history = hist[['date', 'close', 'sma_50', 'sma_200']].to_dict('records')
    except Exception as e:
        print(f"Error fetching yfinance data for {ticker}: {e}")
        price_history = []
    
    return {
        'confluence': confluence_dict,
        'market_data': market_data_dict,
        'signal': signal_dict,
        'price_history': price_history
    }

def create_price_chart(price_data, ticker):
    """Create an interactive price chart with SMAs."""
    if not price_data:
        return None
    
    df = pd.DataFrame(price_data)
    
    fig = go.Figure()
    
    # Price line
    fig.add_trace(go.Scatter(
        x=df['date'],
        y=df['close'],
        name='Price',
        line=dict(color='#FF6B35', width=2),
        mode='lines'
    ))
    
    # SMA 50
    if 'sma_50' in df.columns and df['sma_50'].notna().any():
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['sma_50'],
            name='SMA 50',
            line=dict(color='#4A90E2', width=1.5, dash='dash'),
            mode='lines'
        ))
    
    # SMA 200
    if 'sma_200' in df.columns and df['sma_200'].notna().any():
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['sma_200'],
            name='SMA 200',
            line=dict(color='#9B59B6', width=1.5, dash='dot'),
            mode='lines'
        ))
    
    fig.update_layout(
        title=f"{ticker} Price Chart (1 Year)",
        xaxis_title="Date",
        yaxis_title="Price ($)",
        template="plotly_dark",
        hovermode='x unified',
        height=500,
        showlegend=True,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01
        )
    )
    
    return fig

# Header
st.title("🔬 Ticker Deep Dive")
st.markdown("**Detailed signal validation and confluence analysis**")

# Check database connection
if not DB_CONNECTION:
    st.error("❌ Database connection not configured.")
    st.stop()

# Sidebar - Ticker selector
with st.sidebar:
    st.header("🎯 Select Ticker")
    
    with st.spinner("Loading tickers..."):
        available_tickers = fetch_available_tickers()
    
    if not available_tickers:
        st.error("No tickers found in database")
        st.stop()
    
    # Search/select ticker
    selected_ticker = st.selectbox(
        "Ticker Symbol",
        options=available_tickers,
        index=0,
        help="Select a ticker to analyze"
    )
    
    st.divider()
    
    # Refresh button
    if st.button("🔄 Refresh Data", type="primary"):
        st.cache_data.clear()
        st.rerun()

# Fetch ticker details
if selected_ticker:
    with st.spinner(f"Loading {selected_ticker} data..."):
        data = fetch_ticker_details(selected_ticker)
    
    confluence = data.get('confluence')
    market_data = data.get('market_data')
    signal = data.get('signal')
    price_history = data.get('price_history', [])
    
    # Header section
    col_header1, col_header2 = st.columns([2, 1])
    
    with col_header1:
        st.header(f"📊 {selected_ticker}")
        if signal:
            signal_emoji = {"ACCUMULATE": "🟡", "HOLD": "🔵", "MONITOR": "🟣"}.get(signal['signal_type'], "⚪")
            st.markdown(f"{signal_emoji} **{signal['signal_type']}** Signal • {signal['conviction_level']} Conviction")
        else:
            st.markdown("⚪ No active signal")
    
    with col_header2:
        if market_data and market_data.get('close'):
            st.metric(
                "Current Price",
                f"${market_data['close']:.2f}",
                help="Latest closing price"
            )
    
    st.divider()
    
    # Main content - Two columns
    col_left, col_right = st.columns([1.5, 1])
    
    with col_left:
        # THE NARRATIVE
        st.subheader("📖 The Confluence Narrative")
        
        if confluence:
            # Calculate diversity score if needed
            diversity_score = confluence.get('channel_diversity_score', 0)
            
            # Confluence summary card
            st.markdown(f"""
            <div class="info-card">
                <h3>🎯 Confluence Summary</h3>
                <p><strong>Total Mentions:</strong> {confluence.get('total_mentions', 'N/A')} 
                   (Mentioned: {confluence.get('mentioned_count', 0)}, Inferred: {confluence.get('inferred_count', 0)})</p>
                <p><strong>Unique Channels:</strong> {confluence.get('unique_channels', 'N/A')}</p>
                <p><strong>Unique Themes:</strong> {confluence.get('unique_themes', 'N/A')}</p>
                <p><strong>Sentiment Strength:</strong> {confluence.get('sentiment_strength_score', 0):.1f}/100</p>
                <p><strong>Channel Diversity:</strong> {diversity_score:.1f}/100</p>
                <p><strong>Days Since Last Mention:</strong> {confluence.get('days_since_last_mention', 'N/A')}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Theme breakdown
            if confluence.get('theme_names'):
                st.markdown("#### 🏷️ Primary Themes")
                themes = confluence['theme_names']
                if isinstance(themes, list):
                    for i, theme in enumerate(themes[:5], 1):  # Show top 5
                        st.markdown(f"{i}. {theme}")
                else:
                    st.json(themes)
            
            # Channel categories
            if confluence.get('channel_categories'):
                st.markdown("#### 📺 Channel Categories")
                categories = confluence['channel_categories']
                if isinstance(categories, list):
                    st.write(", ".join(categories))
                else:
                    st.json(categories)
            
            # Videos mentioned
            if confluence.get('videos_mentioned'):
                with st.expander("🎥 View Videos Mentioned"):
                    st.json(confluence['videos_mentioned'])
        else:
            st.info(f"No confluence data available for {selected_ticker}")
        
        # Signal details (if exists)
        if signal:
            st.divider()
            st.subheader("🎯 Active Signal Details")
            
            st.markdown(f"""
            <div class="info-card">
                <h3>Recommendation</h3>
                <p>{signal.get('recommendation', 'N/A')}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Key catalysts
            if signal.get('key_catalysts'):
                st.markdown("#### 🚀 Key Catalysts")
                st.write(signal['key_catalysts'])
            
            # Concerns
            if signal.get('concerns'):
                st.markdown("#### ⚠️ Risk Factors")
                concerns = signal['concerns']
                if isinstance(concerns, list):
                    for concern in concerns:
                        st.markdown(f"• {concern}")
                else:
                    st.json(concerns)
            
            # Price targets
            col_target1, col_target2, col_target3 = st.columns(3)
            with col_target1:
                if signal.get('target_entry_price'):
                    st.metric("Target Entry", f"${signal['target_entry_price']:.2f}")
            with col_target2:
                if signal.get('support_level'):
                    st.metric("Support", f"${signal['support_level']:.2f}")
            with col_target3:
                if signal.get('resistance_level'):
                    st.metric("Resistance", f"${signal['resistance_level']:.2f}")
    
    with col_right:
        # THE NUMBERS
        st.subheader("📊 The Numbers")
        
        if market_data:
            # Valuation metrics
            st.markdown("#### 💰 Valuation Metrics")
            
            # P/E Ratio
            if market_data.get('pe_ratio'):
                pe = market_data['pe_ratio']
                pe_5y_avg = market_data.get('pe_5y_avg', 0)
                pe_delta = f"{((pe / pe_5y_avg - 1) * 100):.1f}% vs 5Y avg" if pe_5y_avg else None
                
                st.markdown(f"""
                <div class="metric-box">
                    <div class="metric-box-value">{pe:.2f}</div>
                    <div class="metric-box-label">P/E Ratio</div>
                    {f'<div class="metric-box-sublabel">{pe_delta}</div>' if pe_delta else ''}
                </div>
                """, unsafe_allow_html=True)
            
            # P/S Ratio
            if market_data.get('ps_ratio'):
                ps = market_data['ps_ratio']
                st.markdown(f"""
                <div class="metric-box">
                    <div class="metric-box-value">{ps:.2f}</div>
                    <div class="metric-box-label">P/S Ratio</div>
                </div>
                """, unsafe_allow_html=True)
            
            # P/B Ratio
            if market_data.get('pb_ratio'):
                pb = market_data['pb_ratio']
                st.markdown(f"""
                <div class="metric-box">
                    <div class="metric-box-value">{pb:.2f}</div>
                    <div class="metric-box-label">P/B Ratio</div>
                </div>
                """, unsafe_allow_html=True)
            
            st.divider()
            st.markdown("#### 💵 Cash Flow Metrics")
            
            # Operating Cash Flow Growth
            if market_data.get('operating_cash_flow_growth'):
                ocf_growth = (market_data['operating_cash_flow_growth'] - 1) * 100
                st.markdown(f"""
                <div class="metric-box">
                    <div class="metric-box-value">{ocf_growth:.1f}%</div>
                    <div class="metric-box-label">OCF Growth</div>
                    <div class="metric-box-sublabel">YoY</div>
                </div>
                """, unsafe_allow_html=True)
            
            # Free Cash Flow Yield
            if market_data.get('free_cash_flow_yield'):
                fcf_yield = market_data['free_cash_flow_yield'] * 100
                st.markdown(f"""
                <div class="metric-box">
                    <div class="metric-box-value">{fcf_yield:.2f}%</div>
                    <div class="metric-box-label">FCF Yield</div>
                </div>
                """, unsafe_allow_html=True)
            
            # TASK 3: Price to Free Cash Flow
            if market_data.get('price_to_free_cash_flow'):
                price_to_fcf = market_data['price_to_free_cash_flow']
                st.markdown(f"""
                <div class="metric-box">
                    <div class="metric-box-value">{price_to_fcf:.2f}</div>
                    <div class="metric-box-label">Price to FCF</div>
                    <div class="metric-box-sublabel">Lower is better</div>
                </div>
                """, unsafe_allow_html=True)
            
            st.divider()
            st.markdown("#### 📈 Technical Indicators")
            
            # RSI
            if market_data.get('rsi_14'):
                rsi = market_data['rsi_14']
                rsi_signal = "Oversold" if rsi < 30 else "Overbought" if rsi > 70 else "Neutral"
                st.markdown(f"""
                <div class="metric-box">
                    <div class="metric-box-value">{rsi:.1f}</div>
                    <div class="metric-box-label">RSI (14)</div>
                    <div class="metric-box-sublabel">{rsi_signal}</div>
                </div>
                """, unsafe_allow_html=True)
            
            # Distance from 52W High
            if market_data.get('distance_from_52w_high_pct'):
                dist_high = market_data['distance_from_52w_high_pct']
                st.markdown(f"""
                <div class="metric-box">
                    <div class="metric-box-value">{dist_high:.1f}%</div>
                    <div class="metric-box-label">From 52W High</div>
                </div>
                """, unsafe_allow_html=True)
            
            # Market Cap
            if market_data.get('market_cap'):
                market_cap_b = market_data['market_cap'] / 1e9
                st.markdown(f"""
                <div class="metric-box">
                    <div class="metric-box-value">${market_cap_b:.1f}B</div>
                    <div class="metric-box-label">Market Cap</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info(f"No market data available for {selected_ticker}")
        
        # Signal score breakdown (if exists)
        if signal:
            st.divider()
            st.markdown("#### 🎯 Signal Score Breakdown")
            
            st.progress(
                float(signal.get('sentiment_score', 0))/100,
                text=f"Sentiment: {signal.get('sentiment_score', 0):.1f}/100"
            )
            st.progress(
                float(signal.get('valuation_score', 0))/100,
                text=f"Valuation: {signal.get('valuation_score', 0):.1f}/100"
            )
            st.progress(
                float(signal.get('technical_score', 0))/100,
                text=f"Technical: {signal.get('technical_score', 0):.1f}/100"
            )
            
            st.metric(
                "Composite Score",
                f"{signal.get('composite_score', 0):.1f}/100",
                help="Weighted average of all scores"
            )
    
    # Price chart (full width at bottom)
    st.divider()
    st.subheader("📈 Price Chart with Moving Averages")
    
    if price_history:
        chart = create_price_chart(price_history, selected_ticker)
        if chart:
            st.plotly_chart(chart, use_container_width=True)
    else:
        st.info(f"No price history available for {selected_ticker}")

# Footer
st.divider()
st.caption("🔬 THEMIS Ticker Deep Dive | Detailed Signal Analysis")
