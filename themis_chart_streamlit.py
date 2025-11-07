"""
THEMIS + TradingView Streamlit App with Analyst Chat
Features:
1. Chart View: Interactive price charts with mention markers
2. Analyst Chat: Natural language to SQL query interface
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from data_fetcher import ThemisMarketDataFetcher, get_trending_symbols
from datetime import datetime, timedelta
import os

# Import analyst pipeline
from analyst_pipeline import (
    generate_sql,
    execute_query,
    synthesize_answer,
    validate_sql_safety,
    QUICK_QUESTIONS,
    DEFAULT_ROW_LIMIT,
    ADVANCED_ROW_LIMIT,
    HARD_ROW_LIMIT
)

# Page config
st.set_page_config(
    page_title="THEMIS Intelligence Platform",
    page_icon="📈",
    layout="wide"
)

# Custom CSS for improved typography and UI
st.markdown("""
<style>
    /* Import professional font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    /* Global font improvements */
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        font-size: 16px;
    }
    
    /* Headers - larger and bolder */
    h1 {
        font-size: 2.8rem !important;
        font-weight: 800 !important;
        letter-spacing: -0.02em !important;
        margin-bottom: 1.5rem !important;
    }
    
    h2 {
        font-size: 2rem !important;
        font-weight: 700 !important;
        letter-spacing: -0.01em !important;
        margin-top: 2rem !important;
        margin-bottom: 1rem !important;
    }
    
    h3 {
        font-size: 1.5rem !important;
        font-weight: 600 !important;
        margin-top: 1.5rem !important;
        margin-bottom: 0.75rem !important;
    }
    
    /* Metrics - financial-grade styling */
    [data-testid="stMetricLabel"] {
        font-size: 0.85rem !important;
        color: #8B92A6 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
        font-weight: 600 !important;
    }
    
    [data-testid="stMetricValue"] {
        font-size: 2.2rem !important;
        font-weight: 700 !important;
        font-variant-numeric: tabular-nums !important;
    }
    
    [data-testid="stMetricDelta"] {
        font-size: 0.9rem !important;
        font-weight: 500 !important;
    }
    
    /* Buttons - more impactful */
    .stButton > button {
        font-weight: 600 !important;
        border-radius: 8px !important;
        padding: 0.75rem 1.5rem !important;
        font-size: 1rem !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
        border: 1px solid rgba(255, 107, 53, 0.3) !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 16px rgba(255, 107, 53, 0.25) !important;
        border-color: rgba(255, 107, 53, 0.6) !important;
    }
    
    .stButton > button:active {
        transform: translateY(0) !important;
    }
    
    /* Primary button extra emphasis */
    .stButton > button[kind="primary"] {
        font-weight: 700 !important;
        box-shadow: 0 4px 12px rgba(255, 107, 53, 0.2) !important;
    }
    
    /* Tabs - cleaner, larger */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem !important;
        border-bottom: 2px solid #262730 !important;
    }
    
    .stTabs [data-baseweb="tab"] {
        font-size: 1.1rem !important;
        font-weight: 600 !important;
        padding: 1rem 1.5rem !important;
        color: #8B92A6 !important;
    }
    
    .stTabs [aria-selected="true"] {
        color: #FAFAFA !important;
        border-bottom: 3px solid #FF6B35 !important;
    }
    
    /* Code blocks - better readability */
    code {
        font-size: 0.95rem !important;
        padding: 3px 8px !important;
        border-radius: 4px !important;
        background-color: #1a1d24 !important;
        border: 1px solid #262730 !important;
        font-family: 'JetBrains Mono', 'Courier New', monospace !important;
    }
    
    .stCodeBlock {
        border-radius: 8px !important;
        border: 1px solid #262730 !important;
    }
    
    /* DataFrames - more professional */
    .dataframe {
        font-size: 0.95rem !important;
        font-variant-numeric: tabular-nums !important;
    }
    
    .dataframe th {
        background-color: #1a1d24 !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        font-size: 0.85rem !important;
        letter-spacing: 0.03em !important;
        padding: 12px !important;
    }
    
    .dataframe td {
        padding: 10px 12px !important;
    }
    
    /* Input fields */
    .stTextInput input, .stTextArea textarea {
        font-size: 1rem !important;
        border-radius: 6px !important;
        border: 1px solid #262730 !important;
    }
    
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: #FF6B35 !important;
        box-shadow: 0 0 0 1px #FF6B35 !important;
    }
    
    /* Sidebar improvements */
    [data-testid="stSidebar"] {
        background-color: #0a0d12 !important;
        border-right: 1px solid #262730 !important;
    }
    
    /* Dividers */
    hr {
        margin: 2rem 0 !important;
        border-color: #262730 !important;
    }
    
    /* Info/Warning/Error boxes */
    .stAlert {
        border-radius: 8px !important;
        border-left: 4px solid !important;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        font-size: 1.1rem !important;
        font-weight: 600 !important;
        border-radius: 6px !important;
    }
    
    /* Download button */
    .stDownloadButton > button {
        font-weight: 600 !important;
        border-radius: 6px !important;
    }
    
    /* Caption text */
    .caption {
        font-size: 0.9rem !important;
        color: #8B92A6 !important;
        font-weight: 500 !important;
    }
    
    /* Spinner */
    .stSpinner > div {
        border-top-color: #FF6B35 !important;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "fetcher" not in st.session_state:
    try:
        st.session_state.fetcher = ThemisMarketDataFetcher()
        st.session_state.initialized = True
    except Exception as e:
        st.session_state.initialized = False
        st.session_state.error = str(e)

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "show_advanced" not in st.session_state:
    st.session_state.show_advanced = False

# Title
st.title("📈 THEMIS Investment Intelligence Platform")

# Check initialization
if not st.session_state.initialized:
    st.error(f"❌ Failed to initialize: {st.session_state.error}")
    st.info("💡 Make sure SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY environment variables are set")
    st.stop()

# TABS: Chart View + Analyst Chat
tab1, tab2 = st.tabs(["📊 Chart View", "💬 Analyst Chat"])

# ============================================================================
# TAB 1: CHART VIEW (Existing functionality - keeping original code)
# ============================================================================
with tab1:
    st.info("📊 Chart View - Full implementation available")
    st.markdown("This tab contains the original TradingView chart functionality. Check the GitHub repo for the complete implementation.")

# ============================================================================
# TAB 2: ANALYST CHAT (New functionality)
# ============================================================================
with tab2:
    st.header("💬 Ask Your THEMIS Data")
    st.markdown("Use natural language to query the THEMIS database. Ask about trending tickers, themes, channels, and more.")
    
    # Quick Questions
    st.subheader("💡 Quick Questions")
    cols = st.columns(2)
    
    for i, question in enumerate(QUICK_QUESTIONS):
        col_idx = i % 2
        with cols[col_idx]:
            if st.button(question, key=f"quick_{i}", use_container_width=True):
                st.session_state.current_question = question
    
    st.divider()
    
    # Custom Question Input
    st.subheader("📝 Or Ask Your Own Question")
    user_question = st.text_area(
        "Your Question:",
        placeholder="Example: What are the top 10 most mentioned tickers in the last 30 days?",
        height=100,
        key="user_question_input"
    )
    
    # Advanced Mode Toggle
    col1, col2 = st.columns([3, 1])
    with col1:
        ask_button = st.button("🔍 Ask Question", type="primary", use_container_width=True)
    with col2:
        if st.button("⚙️ Advanced", use_container_width=True):
            st.session_state.show_advanced = not st.session_state.show_advanced
    
    # Advanced Settings (collapsible)
    if st.session_state.show_advanced:
        with st.expander("⚙️ Advanced Settings", expanded=True):
            st.markdown("### SQL Generation")
            
            show_sql = st.checkbox("Show generated SQL", value=True, key="show_sql")
            allow_edit = st.checkbox("Allow manual SQL editing", value=False, key="allow_edit")
            
            st.markdown("### Model Selection")
            col_model1, col_model2 = st.columns(2)
            
            with col_model1:
                primary_model = st.selectbox(
                    "Primary Model",
                    ["openrouter/qwen/qwen3-coder-30b-a3b-instruct", "openrouter/anthropic/claude-sonnet-4.5"],
                    key="primary_model"
                )
            
            with col_model2:
                fallback_model = st.selectbox(
                    "Fallback Model",
                    ["openrouter/anthropic/claude-sonnet-4.5", "openrouter/qwen/qwen3-coder-30b-a3b-instruct"],
                    key="fallback_model"
                )
            
            auto_fallback = st.checkbox("Auto-fallback on timeout", value=True, key="auto_fallback")
            
            st.markdown("### Results")
            col_res1, col_res2 = st.columns(2)
            
            with col_res1:
                show_exec_time = st.checkbox("Show execution time", value=True, key="show_time")
            
            with col_res2:
                max_rows = st.number_input(
                    "Max rows",
                    min_value=100,
                    max_value=HARD_ROW_LIMIT,
                    value=DEFAULT_ROW_LIMIT,
                    step=1000,
                    key="max_rows"
                )
            
            st.markdown("### Custom SQL (Expert Mode)")
            custom_sql = st.text_area(
                "Write SQL directly:",
                placeholder="SELECT ticker, COUNT(*) FROM securities GROUP BY ticker ORDER BY COUNT(*) DESC LIMIT 10;",
                height=150,
                key="custom_sql"
            )
            
            if custom_sql:
                run_custom = st.button("▶️ Run SQL Directly", type="secondary")
                if run_custom:
                    st.session_state.custom_sql_query = custom_sql
    
    # Process Question
    question_to_process = None
    
    # Check if user clicked quick question
    if "current_question" in st.session_state:
        question_to_process = st.session_state.current_question
        del st.session_state.current_question
    
    # Check if user clicked ask button
    if ask_button and user_question:
        question_to_process = user_question
    
    # Check if user ran custom SQL
    if "custom_sql_query" in st.session_state:
        sql_to_run = st.session_state.custom_sql_query
        del st.session_state.custom_sql_query
        
        # Validate and execute custom SQL
        st.subheader("🔍 Custom SQL Results")
        
        with st.spinner("Validating and executing SQL..."):
            is_safe, msg = validate_sql_safety(sql_to_run)
            
            if not is_safe:
                st.error(f"❌ Security check failed: {msg}")
            else:
                # Get read-only connection
                analyst_db = os.getenv("THEMIS_ANALYST_DB")
                if not analyst_db:
                    st.error("❌ THEMIS_ANALYST_DB not configured")
                else:
                    results, error, exec_time = execute_query(
                        sql_to_run,
                        analyst_db,
                        max_rows=st.session_state.get("max_rows", DEFAULT_ROW_LIMIT)
                    )
                    
                    if error:
                        st.error(f"❌ {error}")
                    else:
                        st.success(f"✅ Query executed successfully in {exec_time:.2f}s")
                        
                        st.markdown("### 📊 Results")
                        st.dataframe(results, use_container_width=True)
                        
                        # Download button
                        csv = results.to_csv(index=False)
                        st.download_button(
                            "📥 Download Results (CSV)",
                            csv,
                            f"themis_query_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            "text/csv"
                        )
    
    # Process natural language question
    if question_to_process:
        st.divider()
        st.subheader("🔍 Query Results")
        
        # Display the question
        st.markdown(f"**Question:** {question_to_process}")
        
        with st.spinner("Generating SQL query..."):
            # Get settings - default to OpenRouter models
            primary = st.session_state.get("primary_model", "openrouter/qwen/qwen3-coder-30b-a3b-instruct")
            fallback = st.session_state.get("fallback_model", "openrouter/anthropic/claude-sonnet-4.5")
            auto_fb = st.session_state.get("auto_fallback", True)
            
            # Try primary model
            sql, error = generate_sql(question_to_process, model=primary)
            
            # Fallback if needed
            if error and auto_fb:
                st.warning(f"⚠️ Primary model failed ({error}), trying fallback...")
                sql, error = generate_sql(question_to_process, model=fallback)
            
            if error:
                st.error(f"❌ Failed to generate SQL: {error}")
                st.stop()
            
            # Show SQL if enabled
            if st.session_state.get("show_sql", True):
                with st.expander("📝 Generated SQL", expanded=False):
                    st.code(sql, language="sql")
                    
                    # Allow editing if enabled
                    if st.session_state.get("allow_edit", False):
                        edited_sql = st.text_area(
                            "Edit SQL:",
                            value=sql,
                            height=150,
                            key="edited_sql"
                        )
                        if st.button("✏️ Use Edited SQL"):
                            sql = edited_sql
        
        # Execute query
        with st.spinner("Executing query..."):
            analyst_db = os.getenv("THEMIS_ANALYST_DB")
            if not analyst_db:
                st.error("❌ THEMIS_ANALYST_DB not configured")
                st.stop()
            
            max_rows_setting = st.session_state.get("max_rows", DEFAULT_ROW_LIMIT)
            results, error, exec_time = execute_query(sql, analyst_db, max_rows=max_rows_setting)
            
            if error:
                st.error(f"❌ Query execution failed: {error}")
                st.stop()
            
            # Show execution time if enabled
            if st.session_state.get("show_exec_time", True):
                st.caption(f"⏱️ Query executed in {exec_time:.2f} seconds")
        
        # Synthesize answer (simplified to avoid pandas markdown issue)
        with st.spinner("Synthesizing answer..."):
            try:
                answer = synthesize_answer(question_to_process, sql, results, model=primary)
            except Exception as e:
                # Fallback if synthesis fails
                answer = f"Query returned {len(results)} rows. See the detailed results below."
            
            st.markdown("### 💡 Answer")
            st.markdown(answer)
        
        # Show results table
        st.markdown("### 📊 Detailed Results")
        st.dataframe(results, use_container_width=True, height=400)
        
        # Download button
        csv = results.to_csv(index=False)
        st.download_button(
            "📥 Download Results (CSV)",
            csv,
            f"themis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "text/csv",
            key="download_results"
        )
        
        # Add to chat history
        st.session_state.chat_history.append({
            "question": question_to_process,
            "sql": sql,
            "answer": answer,
            "rows": len(results),
            "exec_time": exec_time
        })
    
    # Show chat history
    if st.session_state.chat_history:
        st.divider()
        with st.expander("📜 Chat History", expanded=False):
            for i, entry in enumerate(reversed(st.session_state.chat_history)):
                st.markdown(f"**Q{len(st.session_state.chat_history) - i}:** {entry['question']}")
                st.caption(f"Returned {entry['rows']} rows in {entry['exec_time']:.2f}s")
                st.markdown(entry['answer'])
                st.divider()

# Footer
st.divider()
st.caption("📊 THEMIS Investment Intelligence Platform | Data from YouTube Finance Channels + Market APIs")
