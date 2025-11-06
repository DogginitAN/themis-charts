"""
TradingView Lightweight Charts - Python Integration
Uses lightweight-charts-python for custom mention markers.
Better control than widgets, but requires manual data management.
"""

import pandas as pd
from datetime import datetime
from lightweight_charts import Chart
from data_fetcher import fetch_chart_data


def create_themis_chart(symbol: str, days_back: int = 90):
    """
    Create interactive chart with THEMIS mention markers using lightweight-charts.
    
    Args:
        symbol: Security symbol (AAPL, BTC, etc.)
        days_back: Days of historical data
    """
    # Fetch data
    print(f"📊 Loading {symbol} data...")
    data = fetch_chart_data(symbol, days_back)
    
    if data.empty:
        print(f"❌ No data found for {symbol}")
        return
    
    # Create chart
    chart = Chart(
        toolbox=True,
        width=1200,
        height=600
    )
    
    # Set title
    chart.legend(visible=True)
    chart.watermark(f'{symbol}')
    
    # Prepare candlestick data
    price_data = []
    for _, row in data.iterrows():
        price_data.append({
            'time': row['date'].strftime('%Y-%m-%d'),
            'open': float(row['open']),
            'high': float(row['high']),
            'low': float(row['low']),
            'close': float(row['close'])
        })
    
    # Add candlestick series
    chart.set(price_data)
    
    # Add mention markers
    markers = []
    mention_dates = data[data['mention_count'] > 0]
    
    for _, row in mention_dates.iterrows():
        marker_size = min(row['mention_count'] * 0.5 + 1, 3)  # Scale marker size
        
        markers.append({
            'time': row['date'].strftime('%Y-%m-%d'),
            'position': 'aboveBar',
            'color': '#2196F3',
            'shape': 'arrowDown',
            'text': f"{int(row['mention_count'])} mentions",
            'size': marker_size
        })
    
    chart.marker(markers)
    
    # Add volume if available
    volume_data = []
    for _, row in data.iterrows():
        if pd.notna(row['volume']):
            volume_data.append({
                'time': row['date'].strftime('%Y-%m-%d'),
                'value': float(row['volume']),
                'color': '#26a69a' if row['close'] >= row['open'] else '#ef5350'
            })
    
    if volume_data:
        chart.volume(volume_data)
    
    # Show stats
    total_mentions = data['mention_count'].sum()
    days_with_mentions = (data['mention_count'] > 0).sum()
    
    print(f"\n✅ Chart created for {symbol}")
    print(f"📈 Date range: {data['date'].min()} to {data['date'].max()}")
    print(f"🔵 Total mentions: {total_mentions}")
    print(f"📅 Days with mentions: {days_with_mentions}")
    print(f"\n💡 Chart will open in your browser...")
    
    # Display chart (opens in browser)
    chart.show(block=True)


def create_mention_timeline_chart(symbol: str, days_back: int = 90):
    """
    Create a simple line chart showing mention frequency over time.
    
    Args:
        symbol: Security symbol
        days_back: Days of data
    """
    # Fetch data
    data = fetch_chart_data(symbol, days_back)
    
    if data.empty:
        print(f"❌ No data found for {symbol}")
        return
    
    # Create chart
    chart = Chart(
        width=1200,
        height=400
    )
    
    chart.legend(visible=True)
    chart.watermark(f'{symbol} Mention Timeline')
    
    # Prepare mention data as line chart
    mention_data = []
    for _, row in data.iterrows():
        mention_data.append({
            'time': row['date'].strftime('%Y-%m-%d'),
            'value': int(row['mention_count'])
        })
    
    # Create line series
    line = chart.create_line(
        name='Mentions',
        color='#2196F3',
        width=2
    )
    line.set(mention_data)
    
    # Add markers on peaks
    peaks = data.nlargest(5, 'mention_count')
    markers = []
    
    for _, row in peaks.iterrows():
        markers.append({
            'time': row['date'].strftime('%Y-%m-%d'),
            'position': 'aboveBar',
            'color': '#FF5252',
            'shape': 'circle',
            'text': f"Peak: {int(row['mention_count'])}"
        })
    
    line.marker(markers)
    
    print(f"\n✅ Mention timeline chart created for {symbol}")
    chart.show(block=True)


def compare_multiple_securities(symbols: list, days_back: int = 90):
    """
    Compare mention frequency across multiple securities.
    
    Args:
        symbols: List of symbols (e.g., ['AAPL', 'TSLA', 'BTC'])
        days_back: Days of data
    """
    chart = Chart(
        width=1200,
        height=600
    )
    
    chart.legend(visible=True)
    chart.watermark('THEMIS Mention Comparison')
    
    colors = ['#2196F3', '#4CAF50', '#FF9800', '#9C27B0', '#F44336']
    
    for i, symbol in enumerate(symbols):
        data = fetch_chart_data(symbol, days_back)
        
        if data.empty:
            print(f"⚠️  Skipping {symbol} - no data")
            continue
        
        mention_data = []
        for _, row in data.iterrows():
            mention_data.append({
                'time': row['date'].strftime('%Y-%m-%d'),
                'value': int(row['mention_count'])
            })
        
        line = chart.create_line(
            name=symbol,
            color=colors[i % len(colors)],
            width=2
        )
        line.set(mention_data)
        
        print(f"✅ Added {symbol}: {data['mention_count'].sum()} total mentions")
    
    print(f"\n💡 Comparison chart will open in browser...")
    chart.show(block=True)


# Example usage
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="TradingView Lightweight Charts with THEMIS data")
    parser.add_argument("--symbol", type=str, help="Security symbol")
    parser.add_argument("--days", type=int, default=90, help="Days to show")
    parser.add_argument("--type", choices=["price", "timeline", "compare"], default="price",
                        help="Chart type")
    parser.add_argument("--compare", nargs="+", help="Symbols to compare (for --type compare)")
    
    args = parser.parse_args()
    
    try:
        if args.type == "price":
            if not args.symbol:
                print("❌ --symbol required for price chart")
                exit(1)
            create_themis_chart(args.symbol, args.days)
        
        elif args.type == "timeline":
            if not args.symbol:
                print("❌ --symbol required for timeline chart")
                exit(1)
            create_mention_timeline_chart(args.symbol, args.days)
        
        elif args.type == "compare":
            if not args.compare or len(args.compare) < 2:
                print("❌ At least 2 symbols required for comparison")
                print("Example: python lightweight_charts_python.py --type compare --compare AAPL TSLA BTC")
                exit(1)
            compare_multiple_securities(args.compare, args.days)
    
    except KeyboardInterrupt:
        print("\n\n👋 Chart closed")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
