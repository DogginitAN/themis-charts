"""
THEMIS Analyst - Natural Language to SQL Pipeline
Core engine for chat-with-your-data functionality.
"""

import os
import re
import time
import psycopg2
import pandas as pd
from typing import Tuple, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

# Database schema context for LLM
SCHEMA_CONTEXT = """
-- THEMIS Database Schema (5 Core Tables)

CREATE TABLE channels (
    id UUID PRIMARY KEY,
    channel_id TEXT UNIQUE NOT NULL,
    channel_name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE videos (
    id UUID PRIMARY KEY,
    video_id TEXT UNIQUE NOT NULL,
    channel_id UUID REFERENCES channels(id),
    title TEXT NOT NULL,
    published_at TIMESTAMP NOT NULL,  -- When creator uploaded video
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE chunk_analyses (
    id UUID PRIMARY KEY,
    video_id TEXT REFERENCES videos(video_id),
    chunk_index INTEGER NOT NULL,
    start_time_ms INTEGER NOT NULL,
    end_time_ms INTEGER NOT NULL,
    duration_seconds NUMERIC,
    word_count INTEGER,
    core_concepts JSONB,
    analyzed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE investment_themes (
    id UUID PRIMARY KEY,
    chunk_id UUID REFERENCES chunk_analyses(id),
    theme_name TEXT NOT NULL,
    rationale TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE securities (
    id UUID PRIMARY KEY,
    theme_id UUID REFERENCES investment_themes(id),
    ticker TEXT NOT NULL,
    asset_type TEXT CHECK (asset_type IN ('stock', 'crypto', 'etf')),
    source TEXT CHECK (source IN ('mentioned', 'inferred')),  -- mentioned = explicit, inferred = LLM extracted
    reasoning TEXT NOT NULL,
    quote TEXT,  -- Only populated for 'mentioned' source
    created_at TIMESTAMP DEFAULT NOW()
);

-- Key Relationships:
-- channels → videos → chunk_analyses → investment_themes → securities
-- Use video.published_at for timing (not created_at)
-- source='mentioned' = explicitly named, source='inferred' = LLM identified
"""

# Allowed tables (whitelist)
ALLOWED_TABLES = ['channels', 'videos', 'chunk_analyses', 'investment_themes', 'securities']

# Safety limits
DEFAULT_ROW_LIMIT = 10000
ADVANCED_ROW_LIMIT = 50000
HARD_ROW_LIMIT = 100000
QUERY_TIMEOUT_SECONDS = 30


def get_llm_client(model: str, timeout: int = 30):
    """
    Get LLM client configured for the model provider.
    Supports: OpenRouter, LiteLLM proxy, or direct OpenAI.
    """
    # Determine provider from model name
    if model.startswith("openrouter/"):
        # OpenRouter models
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY not set")
        
        return ChatOpenAI(
            model=model.replace("openrouter/", ""),  # Remove prefix
            temperature=0.1,
            max_tokens=2000,
            request_timeout=timeout,
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key
        )
    
    elif model.startswith("ollama/"):
        # LiteLLM proxy (for local Ollama models)
        api_key = os.getenv("LITELLM_PROXY_API_KEY")
        base_url = os.getenv("LITELLM_PROXY_BASE_URL")
        
        if not api_key or not base_url:
            raise ValueError("LITELLM_PROXY_API_KEY and LITELLM_PROXY_BASE_URL must be set for Ollama models")
        
        return ChatOpenAI(
            model=model,
            temperature=0.1,
            max_tokens=2000,
            request_timeout=timeout,
            base_url=base_url,
            api_key=api_key
        )
    
    else:
        # Direct OpenAI or other providers
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPEN_AI")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set")
        
        return ChatOpenAI(
            model=model,
            temperature=0.1,
            max_tokens=2000,
            request_timeout=timeout,
            api_key=api_key
        )


def validate_sql_safety(sql: str) -> Tuple[bool, str]:
    """
    Validate that SQL is safe (read-only, SELECT only).
    
    Returns:
        (is_valid, error_message)
    """
    sql_upper = sql.strip().upper()
    
    # Must start with SELECT
    if not sql_upper.startswith('SELECT'):
        return False, "Only SELECT queries allowed"
    
    # Block dangerous keywords (belt + suspenders, even though we have read-only user)
    dangerous_keywords = [
        r'\bDROP\b', r'\bDELETE\b', r'\bUPDATE\b', r'\bINSERT\b',
        r'\bALTER\b', r'\bCREATE\b', r'\bTRUNCATE\b', r'\bGRANT\b',
        r'\bREVOKE\b', r'\bSET\b', r'\bEXECUTE\b', r'\bCALL\b'
    ]
    
    for pattern in dangerous_keywords:
        if re.search(pattern, sql_upper):
            keyword = pattern.replace(r'\b', '')
            return False, f"Keyword '{keyword}' not allowed"
    
    return True, "Query is safe"


def validate_table_access(sql: str) -> Tuple[bool, str]:
    """
    Ensure query only accesses allowed tables.
    
    Returns:
        (is_valid, error_message)
    """
    sql_upper = sql.upper()
    
    # Simple extraction: look for FROM and JOIN keywords
    # This is not perfect but catches most cases
    for table in ALLOWED_TABLES:
        sql_upper = sql_upper.replace(f'FROM {table.upper()}', 'FROM __ALLOWED__')
        sql_upper = sql_upper.replace(f'JOIN {table.upper()}', 'JOIN __ALLOWED__')
    
    # If we find other table references, block them
    from_pattern = r'FROM\s+([a-zA-Z_][a-zA-Z0-9_]*)'
    join_pattern = r'JOIN\s+([a-zA-Z_][a-zA-Z0-9_]*)'
    
    for pattern in [from_pattern, join_pattern]:
        matches = re.findall(pattern, sql_upper)
        for match in matches:
            if match not in ['__ALLOWED__', 'LATERAL']:  # LATERAL is a keyword, not table
                return False, f"Access to table '{match}' not allowed. Allowed tables: {', '.join(ALLOWED_TABLES)}"
    
    return True, "All tables are allowed"


def apply_row_limit(sql: str, max_rows: int = DEFAULT_ROW_LIMIT) -> str:
    """
    Ensure query has a LIMIT clause. If not, add one.
    If it has a LIMIT > max_rows, reduce it.
    
    Returns:
        Modified SQL with LIMIT
    """
    sql_upper = sql.upper()
    
    # Check if LIMIT already exists
    limit_match = re.search(r'\bLIMIT\s+(\d+)', sql_upper)
    
    if limit_match:
        existing_limit = int(limit_match.group(1))
        if existing_limit > max_rows:
            # Replace with max_rows
            sql = re.sub(r'\bLIMIT\s+\d+', f'LIMIT {max_rows}', sql, flags=re.IGNORECASE)
    else:
        # Add LIMIT
        sql = sql.rstrip(';').strip() + f' LIMIT {max_rows}'
    
    return sql


def clean_llm_response(text: str) -> str:
    """
    Extract SQL from LLM response, handling markdown code blocks.
    """
    text = text.strip()
    
    # Check for ```sql or ``` code blocks
    if text.startswith('```'):
        lines = text.split('\n')
        # Remove first line (```sql or ```)
        lines = lines[1:]
        # Remove last line (```)
        if lines and lines[-1].strip() == '```':
            lines = lines[:-1]
        text = '\n'.join(lines)
    
    return text.strip()


def generate_sql(
    user_question: str,
    model: str = "openrouter/qwen/qwen3-coder-30b-a3b-instruct",
    timeout: int = 30
) -> Tuple[Optional[str], Optional[str]]:
    """
    Generate SQL from natural language question using LLM.
    
    Args:
        user_question: Natural language question
        model: LLM model to use
        timeout: Timeout in seconds
    
    Returns:
        (sql_query, error_message)
        If successful: (sql_query, None)
        If failed: (None, error_message)
    """
    prompt = f"""You are a PostgreSQL expert. Generate a SQL query to answer this question.

DATABASE SCHEMA:
{SCHEMA_CONTEXT}

USER QUESTION:
{user_question}

IMPORTANT INSTRUCTIONS:
1. Return ONLY the SQL query, no explanations or markdown
2. Use video.published_at for date filtering (NOT created_at)
3. For "mentioned" vs "inferred": use securities.source column
4. Join tables properly using the relationships shown above
5. Use standard PostgreSQL syntax
6. Be precise and efficient

Return pure SQL only:
"""
    
    try:
        llm = get_llm_client(model, timeout)
        response = llm.invoke([HumanMessage(content=prompt)])
        sql = clean_llm_response(response.content)
        
        return sql, None
        
    except Exception as e:
        return None, f"LLM generation failed: {str(e)}"


def execute_query(
    sql: str,
    connection_string: str,
    max_rows: int = DEFAULT_ROW_LIMIT,
    timeout: int = QUERY_TIMEOUT_SECONDS
) -> Tuple[Optional[pd.DataFrame], Optional[str], Optional[float]]:
    """
    Execute SQL query with safety checks and timeout.
    
    Args:
        sql: SQL query to execute
        connection_string: Database connection string (read-only)
        max_rows: Maximum rows to return
        timeout: Query timeout in seconds
    
    Returns:
        (dataframe, error_message, execution_time)
        If successful: (df, None, execution_time)
        If failed: (None, error_message, None)
    """
    # Validate safety
    is_safe, msg = validate_sql_safety(sql)
    if not is_safe:
        return None, f"Security check failed: {msg}", None
    
    # Validate table access
    is_allowed, msg = validate_table_access(sql)
    if not is_allowed:
        return None, f"Table access denied: {msg}", None
    
    # Apply row limit
    sql = apply_row_limit(sql, max_rows)
    
    # Execute query
    try:
        conn = psycopg2.connect(connection_string)
        conn.set_session(readonly=True)  # Extra safety
        
        # Set statement timeout
        cursor = conn.cursor()
        cursor.execute(f"SET statement_timeout = {timeout * 1000}")  # milliseconds
        
        start_time = time.time()
        df = pd.read_sql_query(sql, conn)
        execution_time = time.time() - start_time
        
        cursor.close()
        conn.close()
        
        return df, None, execution_time
        
    except psycopg2.Error as e:
        return None, f"Database error: {e.pgerror or str(e)}", None
    except Exception as e:
        return None, f"Execution error: {str(e)}", None


def synthesize_answer(
    user_question: str,
    sql: str,
    results: pd.DataFrame,
    model: str = "openrouter/qwen/qwen3-coder-30b-a3b-instruct"
) -> str:
    """
    Synthesize natural language answer from SQL results.
    
    Args:
        user_question: Original user question
        sql: SQL query that was executed
        results: Query results as DataFrame
        model: LLM model to use
    
    Returns:
        Natural language answer
    """
    # Convert results to a concise summary
    if results.empty:
        return "No results found for your question."
    
    # Limit to first 50 rows for synthesis (don't send huge datasets to LLM)
    results_sample = results.head(50)
    
    # Convert to simple string format instead of markdown
    results_text = results_sample.to_string(index=False)
    
    prompt = f"""You are a financial analyst explaining query results.

USER QUESTION:
{user_question}

SQL QUERY EXECUTED:
{sql}

QUERY RESULTS:
{results_text}

{'...(showing first 50 rows)' if len(results) > 50 else ''}

Provide a clear, concise answer to the user's question based on these results.
Focus on the key insights and numbers. Be specific and professional.
"""
    
    try:
        llm = get_llm_client(model, timeout=30)
        response = llm.invoke([HumanMessage(content=prompt)])
        return response.content.strip()
        
    except Exception as e:
        # Fallback to simple summary if LLM fails
        return f"Query returned {len(results)} rows. See the table below for details."


# Predefined quick questions
QUICK_QUESTIONS = [
    "What are the top 10 most mentioned tickers in the last 30 days?",
    "Show me stocks that were only inferred, never explicitly mentioned",
    "What investment themes are trending this week?",
    "Which channels talk about crypto the most?",
    "What are the most recent mentions in the last 7 days?",
]
