"""
THEMIS + Market Data Fetcher
Combines security mentions from THEMIS database with historical price data
for TradingView chart visualization.
"""

import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import pandas as pd
from supabase import create_client, Client
import yfinance as yf

# Supabase connection
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")


class ThemisMarketDataFetcher:
    """Fetch and merge THEMIS mentions with market price data."""
    
    def __init__(self):
        """Initialize Supabase client."""
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY environment variables")
        
        self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    def get_security_mentions(
        self, 
        symbol: str, 
        days_back: int = 90,
        include_context: bool = True
    ) -> pd.DataFrame:
        """
        Fetch security mentions from THEMIS database.
        
        Args:
            symbol: Security symbol (e.g., 'AAPL', 'BTC')
            days_back: How many days to look back
            include_context: Include video titles and themes
            
        Returns:
            DataFrame with columns: date, mention_count, [context fields]
        """
        cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()
        
        # Query securities table with joins
        query = self.supabase.table("securities").select("""
            security_symbol,
            security_type,
            chunk_analysis_id,
            chunk_analyses!inner(
                id,
                created_at,
                video_id,
                videos!inner(
                    title,
                    published_at,
                    channel_id,
                    channels!inner(channel_name)
                )
            ),
            investment_themes(theme, sentiment)
        """)
        
        # Filters
        query = query.eq("security_symbol", symbol.upper())
        query = query.gte("chunk_analyses.created_at", cutoff_date)
        query = query.order("chunk_analyses.created_at", desc=False)
        
        result = query.execute()
        
        if not result.data:
            return pd.DataFrame()
        
        # Parse nested data
        mentions = []
        for record in result.data:
            chunk = record.get("chunk_analyses", {})
            video = chunk.get("videos", {})
            channel = video.get("channels", {})
            themes = record.get("investment_themes", [])
            
            mention = {
                "symbol": record["security_symbol"],
                "type": record["security_type"],
                "timestamp": chunk.get("created_at"),
                "date": pd.to_datetime(chunk.get("created_at")).date() if chunk.get("created_at") else None,
            }
            
            if include_context:
                mention.update({
                    "video_title": video.get("title"),
                    "channel_name": channel.get("channel_name"),
                    "published_at": video.get("published_at"),
                    "themes": [t.get("theme") for t in themes] if themes else [],
                    "sentiment": themes[0].get("sentiment") if themes else None
                })
            
            mentions.append(mention)
        
        df = pd.DataFrame(mentions)
        
        if df.empty:
            return df
        
        # Aggregate by date
        df_agg = df.groupby("date").agg({
            "symbol": "first",
            "type": "first",
            "timestamp": "count",  # Count mentions per day
        }).rename(columns={"timestamp": "mention_count"}).reset_index()
        
        # If include_context, also aggregate context fields
        if include_context:
            context_agg = df.groupby("date").agg({
                "video_title": lambda x: list(x),
                "channel_name": lambda x: list(x.unique()),
                "themes": lambda x: [theme for sublist in x for theme in sublist],  # Flatten
            }).reset_index()
            
            df_agg = df_agg.merge(context_agg, on="date", how="left")
        
        return df_agg
    
    def get_market_data(
        self,
        symbol: str,
        days_back: int = 90,
        interval: str = "1d"
    ) -> pd.DataFrame:
        """
        Fetch historical market data using yfinance.
        
        Args:
            symbol: Ticker symbol (AAPL, BTC-USD, ETH-USD)
            days_back: Days of historical data
            interval: 1d, 1h, etc.
            
        Returns:
            DataFrame with OHLCV data
        """
        # Handle crypto symbols (convert BTC -> BTC-USD)
        if symbol.upper() in ["BTC", "ETH", "SOL", "ADA", "DOGE", "XRP"]:
            yf_symbol = f"{symbol.upper()}-USD"
        else:
            yf_symbol = symbol.upper()
        
        try:
            ticker = yf.Ticker(yf_symbol)
            
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            # Fetch history
            df = ticker.history(
                start=start_date.strftime("%Y-%m-%d"),
                end=end_date.strftime("%Y-%m-%d"),
                interval=interval
            )
            
            if df.empty:
                print(f"⚠️  No market data found for {yf_symbol}")
                return pd.DataFrame()
            
            # Reset index to get date as column
            df = df.reset_index()
            df["date"] = pd.to_datetime(df["Date"]).dt.date
            
            # Standardize column names
            df = df.rename(columns={
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume"
            })
            
            # Keep only relevant columns
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
        """
        Combine THEMIS mentions and market data into single DataFrame.
        
        Args:
            symbol: Security symbol
            days_back: Days to look back
            include_context: Include video/theme context
            
        Returns:
            DataFrame with columns: date, open, high, low, close, volume, mention_count, [context]
        """
        print(f"📊 Fetching data for {symbol}...")
        
        # Fetch both datasets
        mentions_df = self.get_security_mentions(symbol, days_back, include_context)
        prices_df = self.get_market_data(symbol, days_back)
        
        if prices_df.empty:
            print(f"⚠️  No price data available for {symbol}")
            return pd.DataFrame()
        
        # Merge on date (left join to keep all price dates)
        if not mentions_df.empty:
            merged = prices_df.merge(mentions_df, on="date", how="left")
            # Fill NaN mention_count with 0
            merged["mention_count"] = merged["mention_count"].fillna(0).astype(int)
        else:
            # No mentions found, just return prices with mention_count = 0
            merged = prices_df.copy()
            merged["mention_count"] = 0
        
        # Add symbol column
        merged["symbol"] = symbol.upper()
        
        print(f"✅ Fetched {len(merged)} days of price data")
        print(f"✅ Found {merged['mention_count'].sum()} total mentions")
        
        return merged
    
    def get_trending_securities(self, days: int = 7, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get most mentioned securities in recent period.
        
        Args:
            days: Look back period
            limit: Max results
            
        Returns:
            List of dicts with symbol, type, mention_count
        """
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        result = self.supabase.table("securities").select(
            "security_symbol, security_type, chunk_analysis_id"
        ).gte("created_at", cutoff_date).execute()
        
        if not result.data:
            return []
        
        # Count mentions per symbol
        df = pd.DataFrame(result.data)
        trending = df.groupby(["security_symbol", "security_type"]).size().reset_index(name="mention_count")
        trending = trending.sort_values("mention_count", ascending=False).head(limit)
        
        return trending.to_dict("records")


# Convenience functions for quick usage
def fetch_chart_data(symbol: str, days_back: int = 90) -> pd.DataFrame:
    """Quick function to get chart-ready data."""
    fetcher = ThemisMarketDataFetcher()
    return fetcher.merge_mentions_and_prices(symbol, days_back)


def get_trending_symbols(days: int = 7) -> List[str]:
    """Get list of trending symbols."""
    fetcher = ThemisMarketDataFetcher()
    trending = fetcher.get_trending_securities(days)
    return [t["security_symbol"] for t in trending]


# Example usage
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Fetch THEMIS + market data")
    parser.add_argument("--symbol", type=str, help="Security symbol (e.g., AAPL, BTC)")
    parser.add_argument("--days", type=int, default=90, help="Days to look back")
    parser.add_argument("--trending", action="store_true", help="Show trending securities")
    
    args = parser.parse_args()
    
    fetcher = ThemisMarketDataFetcher()
    
    if args.trending:
        print("\n🔥 Trending Securities (Last 7 Days):")
        trending = fetcher.get_trending_securities(days=7, limit=10)
        for i, sec in enumerate(trending, 1):
            print(f"{i}. {sec['security_symbol']} ({sec['security_type']}) - {sec['mention_count']} mentions")
    
    elif args.symbol:
        data = fetcher.merge_mentions_and_prices(args.symbol, args.days)
        
        if not data.empty:
            print(f"\n📈 {args.symbol} Data Preview:")
            print(data.head(10))
            
            print(f"\n📊 Statistics:")
            print(f"Date Range: {data['date'].min()} to {data['date'].max()}")
            print(f"Total Mentions: {data['mention_count'].sum()}")
            print(f"Days with Mentions: {(data['mention_count'] > 0).sum()}")
            print(f"Avg Mentions/Day: {data['mention_count'].mean():.2f}")
            
            # Days with most mentions
            top_mention_days = data.nlargest(5, "mention_count")[["date", "mention_count", "close"]]
            print(f"\n🔥 Top Mention Days:")
            print(top_mention_days.to_string(index=False))
    
    else:
        print("Usage: python data_fetcher.py --symbol AAPL --days 90")
        print("   or: python data_fetcher.py --trending")
