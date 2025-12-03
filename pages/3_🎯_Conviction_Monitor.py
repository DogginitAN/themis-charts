"""
THEMIS Conviction Monitor - Active Signal Grid
High-density cockpit view of all conviction signals with filtering and sorting.
"""

import streamlit as st
import pandas as pd
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

# Page config
st.set_page_config(
    page_title="Conviction Monitor - THEMIS",
    page_icon="🎯",
    layout="wide"
)

# Custom CSS for dark mode consistency
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    .main {
        font-family: 'Inter', sans-serif;
    }
    
    /* Metric cards */
    .metric-card {
        background: linear-gradient(135deg, #1a1d24 0%, #262730 100%);
        border: 2px solid #3d4858;
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
        transition: all 0.3s;
    }
    
    .metric-card:hover {
        border-color: #FF6B35;
        box-shadow: 0 8px 16px rgba(255, 107, 53, 0.2);
    }
    
    .metric-value {
        font-size: 2.5rem;
        font-weight: 700;
        color: #FF6B35;
        margin-bottom: 0.5rem;
    }
    
    .metric-label {
        font-size: 1rem;
        color: #B8BCC8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
</style>
""", unsafe_allow_html=True)

# Database connection
DB_CONNECTION = os.getenv("THEMIS_ANALYST_DB") or os.getenv("SUPABASE_DB")

def is_empty_value(val):
    """Check if a value is None, empty list, or empty JSON string."""
    if val is None:
        return True
    if isinstance(val, list) and len(val) == 0:
        return True
    if isinstance(val, str) and val in ['[]', '{}', '']:
        return True
    return False

@st.cache_data(ttl=300)
def fetch_actual_themes_for_ticker(ticker):
    """Fetch actual theme names from investment_themes table."""
    conn = psycopg2.connect(DB_CONNECTION, cursor_factory=RealDictCursor)
    
    query = """
    SELECT DISTINCT it.theme_name
    FROM securities s
    INNER JOIN investment_themes it ON s.theme_id = it.id
    WHERE s.ticker = %s
    ORDER BY it.theme_name
    """
    
    try:
        with conn.cursor() as cur:
            cur.execute(query, (ticker,))
            results = cur.fetchall()
            return [row['theme_name'] for row in results]
    finally:
        conn.close()

@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_conviction_signals(signal_type_filter=None, min_score=0):
    """Fetch active conviction signals with market data."""
    
    conn = psycopg2.connect(DB_CONNECTION)
    
    # Build WHERE clause
    where_clauses = ["cs.is_active = TRUE"]
    params = []
    
    if signal_type_filter and signal_type_filter != "All":
        where_clauses.append("cs.signal_type = %s")
        params.append(signal_type_filter)
    
    if min_score > 0:
        where_clauses.append("cs.composite_score >= %s")
        params.append(min_score)
    
    where_clause = " AND ".join(where_clauses)
    
    query = f"""
    SELECT 
        cs.ticker,
        cs.signal_type,
        cs.conviction_level,
        cs.composite_score,
        cs.sentiment_score,
        cs.valuation_score,
        cs.technical_score,
        cs.current_price,
        cs.target_entry_price,
        cs.support_level,
        cs.resistance_level,
        cs.primary_themes,
        cs.key_catalysts,
        cs.recommendation,
        cs.date as signal_date,
        md.close as latest_price,
        md.rsi_14,
        md.pe_ratio,
        md.market_cap,
        md.operating_cash_flow_growth,
        md.free_cash_flow_yield,
        cm.unique_channels,
        cm.total_mentions,
        cm.sentiment_strength_score,
        cm.unique_themes,
        cm.theme_names,
        cm.channel_categories
    FROM conviction_signals cs
    LEFT JOIN market_data md ON cs.ticker = md.ticker
    LEFT JOIN confluence_metrics cm ON cs.ticker = cm.ticker
    WHERE {where_clause}
    ORDER BY cs.composite_score DESC
    """
    
    try:
        df = pd.read_sql_query(query, conn, params=params)
        
        # Populate empty fields from actual database queries
        if not df.empty:
            for idx in df.index:
                ticker = df.at[idx, 'ticker']
                primary_themes = df.at[idx, 'primary_themes']
                key_catalysts = df.at[idx, 'key_catalysts']
                channel_categories = df.at[idx, 'channel_categories']
                unique_channels = df.at[idx, 'unique_channels']
                unique_themes = df.at[idx, 'unique_themes']
                
                # OPTION B: Fetch actual themes from investment_themes table
                if is_empty_value(primary_themes):
                    actual_themes = fetch_actual_themes_for_ticker(ticker)
                    if actual_themes and len(actual_themes) > 0:
                        df.at[idx, 'primary_themes'] = actual_themes[:3]  # Top 3
                
                # If key_catalysts is empty, generate summary
                if is_empty_value(key_catalysts):
                    catalysts_parts = []
                    
                    if unique_channels:
                        catalysts_parts.append(f"{unique_channels} channels")
                    
                    if unique_themes:
                        catalysts_parts.append(f"{unique_themes} themes")
                    
                    if channel_categories and isinstance(channel_categories, list) and len(channel_categories) > 0:
                        top_channels = channel_categories[:2]
                        catalysts_parts.append(f"Top channels: {', '.join(top_channels)}")
                    
                    if catalysts_parts:
                        df.at[idx, 'key_catalysts'] = "Confluence: " + " | ".join(catalysts_parts)
                    else:
                        df.at[idx, 'key_catalysts'] = "Multiple confluence factors"
        
        return df
    finally:
        conn.close()

# Header
st.title("🎯 Conviction Monitor")
st.markdown("**Active signals ranked by composite score** • Real-time strategic sniper opportunities")

# Check database connection
if not DB_CONNECTION:
    st.error("❌ Database connection not configured. Set THEMIS_ANALYST_DB or SUPABASE_DB environment variable.")
    st.stop()

# Sidebar controls
with st.sidebar:
    st.header("⚙️ Filters")
    
    # Signal type filter
    signal_type_filter = st.selectbox(
        "Signal Type",
        ["All", "ACCUMULATE", "HOLD", "MONITOR"],
        index=0
    )
    
    # Min composite score slider
    min_score = st.slider(
        "Min Composite Score",
        min_value=0,
        max_value=100,
        value=50,
        step=5,
        help="Filter signals by minimum composite score (sentiment + valuation + technicals)"
    )
    
    st.divider()
    
    # Refresh button
    if st.button("🔄 Refresh Data", type="primary"):
        st.cache_data.clear()
        st.rerun()

# Fetch data
with st.spinner("Loading conviction signals..."):
    df = fetch_conviction_signals(signal_type_filter, min_score)

# Metrics header
if not df.empty:
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        accumulate_count = len(df[df['signal_type'] == 'ACCUMULATE'])
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{accumulate_count}</div>
            <div class="metric-label">🟡 Accumulate</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        hold_count = len(df[df['signal_type'] == 'HOLD'])
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{hold_count}</div>
            <div class="metric-label">🔵 Hold</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        monitor_count = len(df[df['signal_type'] == 'MONITOR'])
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{monitor_count}</div>
            <div class="metric-label">🟣 Monitor</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        avg_score = df['composite_score'].mean()
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{avg_score:.1f}</div>
            <div class="metric-label">Avg Score</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.divider()

# Display signals grid
if df.empty:
    st.info(f"📭 No active signals found with score ≥ {min_score}")
    st.info("👋 Use the sidebar to adjust filters and find conviction signals.")
else:
    st.subheader(f"📊 {len(df)} Active Signals")
    
    # Format the dataframe for display
    display_df = df.copy()
    
    # Format numeric columns
    display_df['composite_score'] = display_df['composite_score'].apply(lambda x: f"{x:.1f}" if pd.notna(x) else "-")
    display_df['sentiment_score'] = display_df['sentiment_score'].apply(lambda x: f"{x:.1f}" if pd.notna(x) else "-")
    display_df['valuation_score'] = display_df['valuation_score'].apply(lambda x: f"{x:.1f}" if pd.notna(x) else "-")
    display_df['technical_score'] = display_df['technical_score'].apply(lambda x: f"{x:.1f}" if pd.notna(x) else "-")
    
    # Format price columns
    display_df['latest_price'] = display_df['latest_price'].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "-")
    display_df['target_entry_price'] = display_df['target_entry_price'].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "-")
    
    # Format percentage columns
    if 'operating_cash_flow_growth' in display_df.columns:
        display_df['ocf_growth'] = display_df['operating_cash_flow_growth'].apply(
            lambda x: f"{(x-1)*100:.1f}%" if pd.notna(x) and x > 0 else "-"
        )
    
    # Format RSI
    display_df['rsi_14'] = display_df['rsi_14'].apply(lambda x: f"{x:.1f}" if pd.notna(x) else "-")
    
    # Calculate upside
    display_df['upside'] = df.apply(
        lambda row: f"{((row['target_entry_price'] / row['latest_price']) - 1) * 100:.1f}%"
        if pd.notna(row['target_entry_price']) and pd.notna(row['latest_price']) and row['latest_price'] > 0
        else "-",
        axis=1
    )
    
    # Format Primary Themes for display (show top 3 actual themes)
    display_df['themes_display'] = df['primary_themes'].apply(
        lambda x: ", ".join(x[:3]) if isinstance(x, list) and len(x) > 0 else "-"
    )
    
    # Select and rename columns for display
    grid_columns = {
        'ticker': 'Ticker',
        'signal_type': 'Signal',
        'conviction_level': 'Conviction',
        'composite_score': 'Score',
        'latest_price': 'Price',
        'target_entry_price': 'Target',
        'upside': 'Upside',
        'rsi_14': 'RSI',
        'pe_ratio': 'P/E',
        'unique_channels': 'Channels',
        'total_mentions': 'Mentions',
        'themes_display': 'Primary Themes',
        'key_catalysts': 'Key Catalysts'
    }
    
    # Select columns that exist
    available_cols = {k: v for k, v in grid_columns.items() if k in display_df.columns}
    grid_df = display_df[list(available_cols.keys())].rename(columns=available_cols)
    
    # Display the grid with column configuration
    st.dataframe(
        grid_df,
        use_container_width=True,
        height=600,
        column_config={
            "Ticker": st.column_config.TextColumn("Ticker", width="small"),
            "Signal": st.column_config.TextColumn("Signal", width="small"),
            "Conviction": st.column_config.TextColumn("Conviction", width="small"),
            "Score": st.column_config.TextColumn("Score", width="small"),
            "Primary Themes": st.column_config.TextColumn("Primary Themes", width="medium"),
            "Key Catalysts": st.column_config.TextColumn("Key Catalysts", width="large"),
        }
    )
    
    # Expandable details
    st.divider()
    st.subheader("📋 Signal Details")
    
    selected_ticker = st.selectbox(
        "Select ticker for detailed view:",
        options=df['ticker'].tolist(),
        index=0
    )
    
    if selected_ticker:
        signal_row = df[df['ticker'] == selected_ticker].iloc[0]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"### {selected_ticker}")
            st.markdown(f"**Signal:** {signal_row['signal_type']}")
            st.markdown(f"**Conviction:** {signal_row['conviction_level']}")
            st.markdown(f"**Composite Score:** {signal_row['composite_score']:.1f}/100")
            
            st.markdown("#### Score Breakdown")
            st.progress(float(signal_row['sentiment_score'])/100, text=f"Sentiment: {signal_row['sentiment_score']:.1f}")
            st.progress(float(signal_row['valuation_score'])/100, text=f"Valuation: {signal_row['valuation_score']:.1f}")
            st.progress(float(signal_row['technical_score'])/100, text=f"Technical: {signal_row['technical_score']:.1f}")
        
        with col2:
            st.markdown("#### Recommendation")
            st.info(signal_row['recommendation'])
            
            st.markdown("#### Key Catalysts")
            st.write(signal_row['key_catalysts'])
            
            # Show primary themes
            themes = signal_row['primary_themes']
            if themes and isinstance(themes, list) and len(themes) > 0:
                st.markdown("#### Primary Themes")
                for i, theme in enumerate(themes[:5], 1):
                    st.markdown(f"{i}. {theme}")

# Footer
st.divider()
st.caption("🎯 THEMIS Conviction Monitor | Strategic Sniper Signals • Updated every 5 minutes")
