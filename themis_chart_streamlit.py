"""
THEMIS - AI Investment Intelligence Platform
Landing page with navigation to Charting Tool and Analyst Chat
"""

import streamlit as st
from pathlib import Path

# Page config
st.set_page_config(
    page_title="THEMIS",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for landing page
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    /* SIDEBAR NAV HACK - Replace auto-generated home page name */
    [data-testid="stSidebarNav"] li:first-child a div {
        visibility: hidden;
        position: relative;
    }
    
    [data-testid="stSidebarNav"] li:first-child a div::before {
        content: "🏛️ THEMIS";
        visibility: visible;
        position: absolute;
        left: 0;
        top: 0;
        font-weight: 600;
        color: #FAFAFA;
    }
    
    /* Center content */
    .main .block-container {
        max-width: 1200px;
        padding-top: 2rem;
    }
    
    /* Logo container - centered */
    .logo-container {
        display: flex;
        justify-content: center;
        align-items: center;
        margin-bottom: 3rem;
    }
    
    .logo-container img {
        max-width: 500px;
        width: 100%;
        height: auto;
    }
    
    /* Elevator pitch */
    .pitch {
        font-size: 1.3rem;
        line-height: 1.8;
        text-align: center;
        color: #E8E9ED;
        max-width: 900px;
        margin: 0 auto 4rem auto;
        font-weight: 400;
    }
    
    /* Feature cards */
    .feature-card {
        background: linear-gradient(135deg, #1a1d24 0%, #262730 100%);
        border: 2px solid #3d4858;
        border-radius: 16px;
        padding: 2.5rem;
        height: 100%;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    .feature-card:hover {
        transform: translateY(-8px);
        border-color: #FF6B35;
        box-shadow: 0 20px 40px rgba(255, 107, 53, 0.2);
    }
    
    .feature-icon {
        font-size: 3rem;
        margin-bottom: 1rem;
    }
    
    .feature-title {
        font-size: 1.8rem;
        font-weight: 700;
        margin-bottom: 1rem;
        color: #FAFAFA;
    }
    
    .feature-description {
        font-size: 1.1rem;
        line-height: 1.6;
        color: #B8BCC8;
        margin-bottom: 2rem;
    }
    
    /* CTA Buttons */
    .stButton > button {
        width: 100%;
        font-size: 1.2rem !important;
        font-weight: 700 !important;
        padding: 1rem 2rem !important;
        border-radius: 10px !important;
        border: 2px solid #FF6B35 !important;
        background: linear-gradient(135deg, #FF6B35 0%, #FF8C5A 100%) !important;
        color: white !important;
        transition: all 0.3s !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 12px 24px rgba(255, 107, 53, 0.4) !important;
    }
    
    /* Better Together section */
    .together-section {
        background: linear-gradient(135deg, #2d1b4e 0%, #1a1d24 100%);
        border-radius: 16px;
        padding: 3rem;
        margin-top: 4rem;
        border: 2px solid #4a3a6a;
    }
    
    .together-title {
        font-size: 2rem;
        font-weight: 700;
        text-align: center;
        margin-bottom: 1.5rem;
        color: #FAFAFA;
    }
    
    .together-text {
        font-size: 1.2rem;
        line-height: 1.8;
        color: #B8BCC8;
        text-align: center;
        max-width: 800px;
        margin: 0 auto;
    }
    
    /* Hide Streamlit branding on home page */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Logo - Centered
logo_path = Path("assets/themis_logo.png")
if logo_path.exists():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image(str(logo_path), use_column_width=True)
else:
    st.markdown('<div style="text-align: center; font-size: 8rem; margin: 2rem 0;">🏛️</div>', unsafe_allow_html=True)

# Elevator Pitch
st.markdown('''
<div class="pitch">
THEMIS transforms the vast ocean of expert commentary into actionable investment intelligence. 
We go beyond explicit mentions, using advanced AI to uncover hidden, inferred opportunities 
across millions of hours of content. Get a decisive edge with visual analytics and AI-powered 
insights that surface what others miss.
</div>
''', unsafe_allow_html=True)

# Feature Cards
col1, col2 = st.columns(2, gap="large")

with col1:
    st.markdown('''
    <div class="feature-card">
        <div class="feature-icon">📈</div>
        <div class="feature-title">Charting Tool</div>
        <div class="feature-description">
            Visualize investment signals on TradingView-style charts. See exactly when securities 
            were mentioned on YouTube, correlate buzz with price action, and identify if mentions 
            preceded market moves.
            <br><br>
            <strong>Perfect for:</strong>
            <ul>
                <li>Signal validation & timing analysis</li>
                <li>Portfolio monitoring & conviction checks</li>
                <li>Backtesting mention-to-price correlation</li>
            </ul>
        </div>
    </div>
    ''', unsafe_allow_html=True)
    
    if st.button("📈 Launch Charting Tool →", key="chart_cta", type="primary"):
        st.switch_page("pages/1_📈_Charting_Tool.py")

with col2:
    st.markdown('''
    <div class="feature-card">
        <div class="feature-icon">💬</div>
        <div class="feature-title">Analyst Chat</div>
        <div class="feature-description">
            Ask questions in plain English, get SQL-powered answers from the THEMIS database. 
            Discover trending tickers, hidden gems, emerging themes, and channel insights without 
            writing a single line of code.
            <br><br>
            <strong>Perfect for:</strong>
            <ul>
                <li>Discovery & exploration (unknown unknowns)</li>
                <li>Trend identification & theme analysis</li>
                <li>Custom research & data deep-dives</li>
            </ul>
        </div>
    </div>
    ''', unsafe_allow_html=True)
    
    if st.button("💬 Launch Analyst Chat →", key="chat_cta", type="primary"):
        st.switch_page("pages/2_💬_Analyst_Chat.py")

# Better Together Section
st.markdown('''
<div class="together-section">
    <div class="together-title">🔗 Better Together</div>
    <div class="together-text">
        The magic happens when you combine both tools. Use <strong>Analyst Chat</strong> to ask 
        "What are the most discussed AI stocks this month?" and discover emerging opportunities. 
        Then jump to the <strong>Charting Tool</strong> to visualize those tickers, see the exact 
        mention timeline, and validate if the YouTube buzz preceded price movements. 
        <br><br>
        <strong>Discovery → Validation → Action</strong> — all in one platform.
    </div>
</div>
''', unsafe_allow_html=True)

# Stats Section
st.divider()
st.markdown("### 📊 THEMIS Intelligence Database")

col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)

with col_stat1:
    st.metric("Securities Tracked", "2,668+", help="Unique tickers extracted from videos")

with col_stat2:
    st.metric("AI Inferences", "65%", help="Percentage of securities identified via LLM context analysis")

with col_stat3:
    st.metric("Top Channels", "10+", help="Leading finance YouTube channels monitored")

with col_stat4:
    st.metric("Historical Coverage", "2022-2025", help="Years of video content analyzed")

# Footer
st.divider()
st.caption("📊 THEMIS Investment Intelligence Platform | Powered by AI, Built for Investors")
st.caption("⚖️ Named after the Greek goddess of divine order, fairness, and impartial judgment")
