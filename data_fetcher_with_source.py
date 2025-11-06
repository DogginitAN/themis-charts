"""
THEMIS + Market Data Fetcher - WITH SOURCE FILTER
Uses video.published_at for mention timestamps (when video was published)
instead of securities.created_at (when we analyzed it).
Includes channel names and source type (mentioned vs inferred).
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
        
        # Step 1: Get securities with this ticker
        query = self.supabase.table("securities").select(
            "id, ticker, asset_type, theme_id, source"
        ).eq("ticker", symbol.upper())
        
        # Filter by source if needed
        if not include_inferred:
            query = query.eq("source", "mentioned")
        
        securities_result = query.execute()
        
        if not securities_result.data:
            return pd.DataFrame()
        
        theme_ids = [s["theme_id"] for s in securities_result.data if s.get("theme_id")]
        
        if not theme_ids:
            return pd.DataFrame()
        
        # Step 2: Get investment_themes
        themes_result = self.supabase.table("investment_themes").select(
            "id, chunk_id, theme_name"
        ).in_("id", theme_ids).execute()
        
        if not themes_result.data:
            return pd.DataFrame()
        
        chunk_ids = [t["chunk_id"] for t in themes_result.data if t.get("chunk_id")]
        
        if not chunk_ids:
            return pd.DataFrame()
        
        # Step 3: Get chunk_analyses with video_id
        chunks_result = self.supabase.table("chunk_analyses").select(
            "id, video_id"
        ).in_("id", chunk_ids).execute()
        
        if not chunks_result.data:
            return pd.DataFrame()
        
        video_ids = list(set([c["video_id"] for c in chunks_result.data if c.get("video_id")]))
        
        if not video_ids:
            return pd.DataFrame()
        
        # Step 4: Get videos with published_at and channel_id
        videos_result = self.supabase.table("videos").select(
            "video_id, published_at, title, channel_id"
        ).in_("video_id", video_ids).gte("published_at", cutoff_date).execute()
        
        if not videos_result.data:
            return pd.DataFrame()
        
        # Step 5: Get channel names if include_context
        channel_map = {}
        if include_context:
            channel_ids = list(set([v["channel_id"] for v in videos_result.data if v.get("channel_id")]))
            
            if channel_ids:
                channels_result = self.supabase.table("channels").select(
                    "id, channel_name"
                ).in_("id", channel_ids).execute()
                
                if channels_result.data:
                    channel_map = {c["id"]: c["channel_name"] for c in channels_result.data}
        
        # Build lookup maps
        video_map = {v["video_id"]: v for v in videos_result.data}
        chunk_map = {c["id"]: c for c in chunks_result.data}
        theme_map = {t["id"]: t for t in themes_result.data}
        
        # Build mentions list using VIDEO PUBLISHED DATE
        mentions = []
        for sec in securities_result.data:
            theme = theme_map.get(sec["theme_id"])
            if not theme:
                continue
            
            chunk = chunk_map.get(theme["chunk_id"])
            if not chunk:
                continue
            
            video = video_map.get(chunk["video_id"])
            if not video:
                continue
            
            published_at = video.get("published_at")
            if not published_at:
                continue
            
            # USE VIDEO PUBLISHED DATE (not securities.created_at)
            date_obj = pd.to_datetime(published_at).date()
            
            mention = {
                "symbol": sec["ticker"],
                "type": str(sec["asset_type"]),
                "source": sec["source"],  # Add source type
                "date": date_obj,
            }
            
            if include_context:
                mention["theme_name"] = theme.get("theme_name")
                mention["video_title"] = video.get("title")
                # Add channel name
                channel_id = video.get("channel_id")
                mention["channel_name"] = channel_map.get(channel_id, "Unknown Channel")
            
            mentions.append(mention)
        
        if not mentions:
            return pd.DataFrame()
        
        df = pd.DataFrame(mentions)
        
        # Aggregate by date AND source
        agg_dict = {
            "symbol": "first",
            "type": "first",
        }
        
        if include_context:
            agg_dict["theme_name"] = lambda x: list(x)
            agg_dict["video_title"] = lambda x: list(x)
            agg_dict["channel_name"] = lambda x: list(set(x))  # Unique channels per day
        
        # Group by date and source to count each type separately
        df["mention_count"] = 1
        
        # Pivot to get mentioned_count and inferred_count
        source_counts = df.groupby(["date", "source"]).size().unstack(fill_value=0)
        
        # Aggregate other fields by date only
        df_agg = df.groupby("date").agg(agg_dict).reset_index()
        df_agg["mention_count"] = df.groupby("date").size().values
        
        # Add source breakdown
        if "mentioned" in source_counts.columns:
            df_agg["mentioned_count"] = df_agg["date"].map(source_counts["mentioned"]).fillna(0).astype(int)
        else:
            df_agg["mentioned_count"] = 0
            
        if "inferred" in source_counts.columns:
            df_agg["inferred_count"] = df_agg["date"].map(source_counts["inferred"]).fillna(0).astype(int)
        else:
            df_agg["inferred_count"] = 0
        
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
        include_context: bool = True,
        include_inferred: bool = True
    ) -> pd.DataFrame:
        """Combine THEMIS mentions and market data."""
        print(f"📊 Fetching data for {symbol}...")
        
        mentions_df = self.get_security_mentions(symbol, days_back, include_context, include_inferred)
        prices_df = self.get_market_data(symbol, days_back)
        
        if prices_df.empty:
            print(f"⚠️  No price data available for {symbol}")
            return pd.DataFrame()
        
        if not mentions_df.empty:
            merged = prices_df.merge(mentions_df, on="date", how="left")
            merged["mention_count"] = merged["mention_count"].fillna(0).astype(int)
            merged["mentioned_count"] = merged.get("mentioned_count", pd.Series(0)).fillna(0).astype(int)
            merged["inferred_count"] = merged.get("inferred_count", pd.Series(0)).fillna(0).astype(int)
        else:
            merged = prices_df.copy()
            merged["mention_count"] = 0
            merged["mentioned_count"] = 0
            merged["inferred_count"] = 0
        
        merged["symbol"] = symbol.upper()
        
        print(f"✅ Fetched {len(merged)} days of price data")
        print(f"✅ Found {merged['mention_count'].sum()} total mentions")
        if "mentioned_count" in merged.columns:
            print(f"   - {merged['mentioned_count'].sum()} explicit mentions")
            print(f"   - {merged['inferred_count'].sum()} inferred mentions")
        
        return merged
    
    def get_trending_securities(self, days: int = 7, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most mentioned securities in recent period."""
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        # Get recent securities
        securities_result = self.supabase.table("securities").select(
            "ticker, asset_type, created_at"
        ).gte("created_at", cutoff_date).execute()
        
        if not securities_result.data:
            return []
        
        # Count mentions
        securities_list = []
        for sec in securities_result.data:
            securities_list.append({
                "ticker": sec["ticker"],
                "asset_type": str(sec["asset_type"])
            })
        
        df = pd.DataFrame(securities_list)
        trending = df.groupby(["ticker", "asset_type"]).size().reset_index(name="mention_count")
        trending = trending.sort_values("mention_count", ascending=False).head(limit)
        
        trending = trending.rename(columns={
            "ticker": "security_symbol",
            "asset_type": "security_type"
        })
        
        return trending.to_dict("records")


def fetch_chart_data(symbol: str, days_back: int = 90, include_inferred: bool = True) -> pd.DataFrame:
    """Quick function to get chart-ready data."""
    fetcher = ThemisMarketDataFetcher()
    return fetcher.merge_mentions_and_prices(symbol, days_back, include_inferred=include_inferred)


def get_trending_symbols(days: int = 7) -> List[str]:
    """Get list of trending symbols."""
    fetcher = ThemisMarketDataFetcher()
    trending = fetcher.get_trending_securities(days)
    return [t["security_symbol"] for t in trending]
