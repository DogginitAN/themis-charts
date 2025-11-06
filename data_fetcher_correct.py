"""
THEMIS + Market Data Fetcher - CORRECT SCHEMA VERSION
Matches actual database structure:
- securities.ticker (not security_symbol)
- securities.asset_type (not security_type)
- securities.theme_id → investment_themes.chunk_id → chunk_analyses
"""

import os
from datetime import datetime, timedelta
from typing import List, Dict, Any
import pandas as pd
from supabase import create_client, Client
import yfinance as yf

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")


class ThemisMarketDataFetcher:
    """Fetch and merge THEMIS mentions with market price data."""
    
    def __init__(self):
        """Initialize Supabase client."""
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
        
        self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    def get_security_mentions(
        self, 
        symbol: str, 
        days_back: int = 90,
        include_context: bool = True
    ) -> pd.DataFrame:
        """
        Fetch security mentions from THEMIS database.
        Uses actual schema: securities.ticker, securities.theme_id
        """
        cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()
        
        # Step 1: Get securities with this ticker
        securities_result = self.supabase.table("securities").select(
            "id, ticker, asset_type, theme_id, created_at"
        ).eq("ticker", symbol.upper()).execute()
        
        if not securities_result.data:
            return pd.DataFrame()
        
        # Get theme_ids
        theme_ids = [s["theme_id"] for s in securities_result.data if s.get("theme_id")]
        
        if not theme_ids:
            return pd.DataFrame()
        
        # Step 2: Get investment_themes for these theme_ids
        themes_result = self.supabase.table("investment_themes").select(
            "id, chunk_id, theme_name, created_at"
        ).in_("id", theme_ids).execute()
        
        if not themes_result.data:
            return pd.DataFrame()
        
        # Get chunk_ids
        chunk_ids = [t["chunk_id"] for t in themes_result.data if t.get("chunk_id")]
        
        if not chunk_ids:
            return pd.DataFrame()
        
        # Step 3: Get chunk_analyses
        chunks_result = self.supabase.table("chunk_analyses").select(
            "id, created_at, video_id"
        ).in_("id", chunk_ids).gte("created_at", cutoff_date).execute()
        
        if not chunks_result.data:
            return pd.DataFrame()
        
        # Build mentions list
        mentions = []
        chunk_map = {c["id"]: c for c in chunks_result.data}
        theme_map = {t["id"]: t for t in themes_result.data}
        
        for sec in securities_result.data:
            theme = theme_map.get(sec["theme_id"])
            if not theme:
                continue
            
            chunk = chunk_map.get(theme["chunk_id"])
            if not chunk:
                continue
            
            created_at = chunk.get("created_at")
            if not created_at:
                continue
            
            date_obj = pd.to_datetime(created_at).date()
            
            mention = {
                "symbol": sec["ticker"],
                "type": sec["asset_type"],
                "date": date_obj,
            }
            
            if include_context:
                mention["theme_name"] = theme.get("theme_name")
            
            mentions.append(mention)
        
        if not mentions:
            return pd.DataFrame()
        
        df = pd.DataFrame(mentions)
        
        # Aggregate by date
        agg_dict = {
            "symbol": "first",
            "type": "first",
        }
        
        if include_context:
            agg_dict["theme_name"] = lambda x: list(x)
        
        df_agg = df.groupby("date").agg(agg_dict).reset_index()
        df_agg["mention_count"] = df.groupby("date").size().values
        
        return df_agg
    
    def get_market_data(
        self,
        symbol: str,
        days_back: int = 90,
        interval: str = "1d"
    ) -> pd.DataFrame:
        """Fetch historical market data using yfinance."""
        # Handle crypto symbols
        if symbol.upper() in ["BTC", "ETH", "SOL", "ADA", "DOGE", "XRP", "AVAX", "MATIC", "DOT", "LINK"]:
            yf_symbol = f"{symbol.upper()}-USD"
        else:
            yf_symbol = symbol.upper()
        
        try:
            ticker = yf.Ticker(yf_symbol)
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            df = ticker.history(
                start=start_date.strftime("%Y-%m-%d"),
                end=end_date.strftime("%Y-%m-%d"),
                interval=interval
            )
            
            if df.empty:
                print(f"⚠️  No market data found for {yf_symbol}")
                return pd.DataFrame()
            
            df = df.reset_index()
            df["date"] = pd.to_datetime(df["Date"]).dt.date
            
            df = df.rename(columns={
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume"
            })
            
            df = df[["date", "open", "high", "low", "close", "volume"]]
            
            return df
            
        except Exception as e:
            print(f"❌ Error fetching market data for {yf_symbol}: {e}")
            return pd.DataFrame()
    
    def merge_mentions_and_prices(
        self,
        symbol: str,
        days_back: int = 90,
        include_context: bool = True
    ) -> pd.DataFrame:
        """Combine THEMIS mentions and market data."""
        print(f"📊 Fetching data for {symbol}...")
        
        mentions_df = self.get_security_mentions(symbol, days_back, include_context)
        prices_df = self.get_market_data(symbol, days_back)
        
        if prices_df.empty:
            print(f"⚠️  No price data available for {symbol}")
            return pd.DataFrame()
        
        if not mentions_df.empty:
            merged = prices_df.merge(mentions_df, on="date", how="left")
            merged["mention_count"] = merged["mention_count"].fillna(0).astype(int)
        else:
            merged = prices_df.copy()
            merged["mention_count"] = 0
        
        merged["symbol"] = symbol.upper()
        
        print(f"✅ Fetched {len(merged)} days of price data")
        print(f"✅ Found {merged['mention_count'].sum()} total mentions")
        
        return merged
    
    def get_trending_securities(self, days: int = 7, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most mentioned securities in recent period."""
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        # Get recent investment_themes
        themes_result = self.supabase.table("investment_themes").select(
            "id, chunk_id, created_at"
        ).gte("created_at", cutoff_date).execute()
        
        if not themes_result.data:
            return []
        
        theme_ids = [t["id"] for t in themes_result.data]
        
        # Get securities for these themes
        securities_result = self.supabase.table("securities").select(
            "ticker, asset_type, theme_id"
        ).in_("theme_id", theme_ids).execute()
        
        if not securities_result.data:
            return []
        
        # Count mentions
        df = pd.DataFrame(securities_result.data)
        trending = df.groupby(["ticker", "asset_type"]).size().reset_index(name="mention_count")
        trending = trending.sort_values("mention_count", ascending=False).head(limit)
        
        # Rename columns to match expected format
        trending = trending.rename(columns={
            "ticker": "security_symbol",
            "asset_type": "security_type"
        })
        
        return trending.to_dict("records")


def fetch_chart_data(symbol: str, days_back: int = 90) -> pd.DataFrame:
    """Quick function to get chart-ready data."""
    fetcher = ThemisMarketDataFetcher()
    return fetcher.merge_mentions_and_prices(symbol, days_back)


def get_trending_symbols(days: int = 7) -> List[str]:
    """Get list of trending symbols."""
    fetcher = ThemisMarketDataFetcher()
    trending = fetcher.get_trending_securities(days)
    return [t["security_symbol"] for t in trending]
