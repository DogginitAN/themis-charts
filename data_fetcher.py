"""
THEMIS + Market Data Fetcher - PostgreSQL Direct Connection
Uses video.published_at for mention timestamps (when video was published)
instead of securities.created_at (when we analyzed it).
Includes channel names and source type (mentioned vs inferred).
"""

import os
from datetime import datetime, timedelta
from typing import List, Dict, Any
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import yfinance as yf

# Use the THEMIS_ANALYST_DB (read-only) connection
DB_CONNECTION = os.getenv("THEMIS_ANALYST_DB") or os.getenv("SUPABASE_DB")


class ThemisMarketDataFetcher:
    """Fetch and merge THEMIS mentions with market price data."""
    
    def __init__(self):
        """Initialize database connection."""
        if not DB_CONNECTION:
            raise ValueError("Missing THEMIS_ANALYST_DB or SUPABASE_DB environment variable")
        
        self.db_connection = DB_CONNECTION
    
    def _get_connection(self):
        """Create a new database connection."""
        return psycopg2.connect(self.db_connection)
    
    def _get_dict_connection(self):
        """Create a connection with RealDictCursor for dict results."""
        return psycopg2.connect(self.db_connection, cursor_factory=RealDictCursor)
    
    def get_security_mentions(
        self, 
        symbol: str, 
        days_back: int = 90,
        include_context: bool = True,
        include_inferred: bool = True
    ) -> pd.DataFrame:
        """
        Fetch security mentions from THEMIS database.
        Uses video.published_at for timestamps (not securities.created_at).
        Includes channel names when include_context=True.
        
        Args:
            symbol: Security ticker
            days_back: Days to look back
            include_context: Include video/channel/theme context
            include_inferred: Include 'inferred' mentions (not just 'mentioned')
        """
        cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()
        
        # Build SQL query with joins
        source_filter = "" if include_inferred else "AND s.source = 'mentioned'"
        
        context_fields = ""
        if include_context:
            context_fields = ", it.theme_name, v.title as video_title, c.channel_name"
        
        query = f"""
        SELECT 
            s.ticker as symbol,
            s.asset_type as type,
            s.source,
            v.published_at::date as date
            {context_fields}
        FROM securities s
        INNER JOIN investment_themes it ON s.theme_id = it.id
        INNER JOIN chunk_analyses ca ON it.chunk_id = ca.id
        INNER JOIN videos v ON ca.video_id = v.video_id
        {'INNER JOIN channels c ON v.channel_id = c.id' if include_context else ''}
        WHERE s.ticker = %s
        AND v.published_at >= %s
        {source_filter}
        ORDER BY v.published_at DESC
        """
        
        # Use regular connection (not RealDictCursor) for pandas compatibility
        conn = self._get_connection()
        try:
            df = pd.read_sql_query(query, conn, params=(symbol.upper(), cutoff_date))
            
            if df.empty:
                return pd.DataFrame()
            
            # The date column is already a date object from PostgreSQL ::date cast
            # No need to convert - it's already datetime.date objects
            
            # Count mentions by date and source
            source_counts = df.groupby(['date', 'source']).size().unstack(fill_value=0)
            
            # Aggregate other fields by date
            agg_dict = {
                'symbol': 'first',
                'type': 'first',
            }
            
            if include_context:
                agg_dict['theme_name'] = lambda x: list(x)
                agg_dict['video_title'] = lambda x: list(x)
                agg_dict['channel_name'] = lambda x: list(set(x))
            
            df_agg = df.groupby('date').agg(agg_dict).reset_index()
            df_agg['mention_count'] = df.groupby('date').size().values
            
            # Add source breakdown
            if 'mentioned' in source_counts.columns:
                df_agg['mentioned_count'] = df_agg['date'].map(source_counts['mentioned']).fillna(0).astype(int)
            else:
                df_agg['mentioned_count'] = 0
                
            if 'inferred' in source_counts.columns:
                df_agg['inferred_count'] = df_agg['date'].map(source_counts['inferred']).fillna(0).astype(int)
            else:
                df_agg['inferred_count'] = 0
            
            return df_agg
            
        finally:
            conn.close()
    
    def get_market_data(
        self,
        symbol: str,
        days_back: int = 90,
        asset_type: str = "stock"
    ) -> pd.DataFrame:
        """
        Fetch market price data from yfinance.
        
        Args:
            symbol: Ticker symbol
            days_back: Days to look back
            asset_type: 'stock' or 'crypto'
        """
        # Map crypto symbols for yfinance
        yf_symbol = symbol
        if asset_type.lower() in ["crypto", "cryptocurrency"]:
            if not symbol.endswith("-USD"):
                yf_symbol = f"{symbol}-USD"
        
        start_date = datetime.now() - timedelta(days=days_back)
        
        try:
            ticker = yf.Ticker(yf_symbol)
            df = ticker.history(start=start_date, interval="1d")
            
            if df.empty:
                return pd.DataFrame()
            
            # Reset index to get date as a column
            df = df.reset_index()
            df['date'] = pd.to_datetime(df['Date']).dt.date
            df = df.rename(columns={
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            })
            
            return df[['date', 'open', 'high', 'low', 'close', 'volume']]
            
        except Exception as e:
            print(f"Error fetching market data for {yf_symbol}: {e}")
            return pd.DataFrame()
    
    def merge_mentions_and_prices(
        self,
        symbol: str,
        days_back: int = 90,
        include_context: bool = True,
        include_inferred: bool = True
    ) -> pd.DataFrame:
        """
        Merge security mentions with market price data.
        Returns a DataFrame with daily prices and mention counts.
        """
        mentions = self.get_security_mentions(
            symbol, 
            days_back=days_back, 
            include_context=include_context,
            include_inferred=include_inferred
        )
        
        asset_type = "stock"
        if not mentions.empty and 'type' in mentions.columns:
            asset_type = str(mentions['type'].iloc[0])
        
        prices = self.get_market_data(symbol, days_back=days_back, asset_type=asset_type)
        
        if prices.empty:
            return pd.DataFrame()
        
        # Merge on date
        if mentions.empty:
            merged = prices.copy()
            merged['mention_count'] = 0
            merged['mentioned_count'] = 0
            merged['inferred_count'] = 0
        else:
            merged = prices.merge(mentions, on='date', how='left')
            merged['mention_count'] = merged['mention_count'].fillna(0).astype(int)
            merged['mentioned_count'] = merged['mentioned_count'].fillna(0).astype(int)
            merged['inferred_count'] = merged['inferred_count'].fillna(0).astype(int)
        
        return merged.sort_values('date')
    
    def get_trending_securities(
        self, 
        days: int = 7, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get the most mentioned securities in the last N days.
        
        Args:
            days: Days to look back
            limit: Number of results to return
        """
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        query = """
        SELECT 
            s.ticker as security_symbol,
            s.asset_type as security_type,
            COUNT(*) as mention_count
        FROM securities s
        INNER JOIN investment_themes it ON s.theme_id = it.id
        INNER JOIN chunk_analyses ca ON it.chunk_id = ca.id
        INNER JOIN videos v ON ca.video_id = v.video_id
        WHERE v.published_at >= %s
        GROUP BY s.ticker, s.asset_type
        ORDER BY mention_count DESC
        LIMIT %s
        """
        
        # Use RealDictCursor for dict results (not pandas)
        conn = self._get_dict_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, (cutoff_date, limit))
            results = cursor.fetchall()
            return [dict(row) for row in results]
        finally:
            conn.close()


def get_trending_symbols(days: int = 7, limit: int = 10) -> List[str]:
    """Helper function to get just the trending symbols."""
    fetcher = ThemisMarketDataFetcher()
    trending = fetcher.get_trending_securities(days=days, limit=limit)
    return [t['security_symbol'] for t in trending]
