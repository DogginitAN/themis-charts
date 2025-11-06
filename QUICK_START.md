# 🚀 THEMIS TradingView Integration - Quick Start

## Overview
Three ways to visualize THEMIS security mentions on price charts:

1. **Streamlit App** (⚡ Fastest) - Interactive web app with TradingView widgets
2. **Lightweight Charts** (🎨 Custom) - Python standalone charts with markers
3. **React Component** (🚀 Production) - Next.js/React for full platform

---

## Option 1: Streamlit App (RECOMMENDED FOR MVP)

### Setup
```bash
cd /workspace/tradingview_integration

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export SUPABASE_URL="your_supabase_url"
export SUPABASE_SERVICE_ROLE_KEY="your_service_role_key"

# Run the app
streamlit run themis_chart_streamlit.py
```

### Usage
1. App opens in browser (usually http://localhost:8501)
2. Enter symbol in sidebar (AAPL, TSLA, BTC, ETH, etc.)
3. Adjust date range (7-365 days)
4. Click "Load Chart"
5. View TradingView widget + custom interactive chart with mention markers

### Features
- ✅ TradingView full chart widget (free)
- ✅ Custom Plotly chart with mention markers
- ✅ Mention timeline bar chart
- ✅ Trending securities sidebar
- ✅ Detailed mention context table
- ✅ CSV export

### Screenshots
- **TradingView Widget**: Professional chart with RSI, MA indicators
- **Custom Chart**: Candlesticks with blue triangle markers = mentions
- **Mention Details**: See which videos/channels mentioned the security

---

## Option 2: Lightweight Charts (Python)

### Setup
```bash
pip install lightweight-charts-python
```

### Usage

#### Price Chart with Mention Markers
```bash
python lightweight_charts_python.py --symbol AAPL --days 90 --type price
```

#### Mention Timeline Only
```bash
python lightweight_charts_python.py --symbol BTC --days 30 --type timeline
```

#### Compare Multiple Securities
```bash
python lightweight_charts_python.py --type compare --compare AAPL TSLA NVDA --days 90
```

### Features
- ✅ Opens in browser (interactive)
- ✅ Custom mention markers on candlesticks
- ✅ Volume overlay
- ✅ No API keys needed (uses local data)
- ✅ Export to PNG/SVG

---

## Option 3: React Component (Next.js)

### Setup
```bash
# In your Next.js project
npm install lightweight-charts
```

### Usage

#### Copy Component
```bash
cp ThemisChart.tsx your-nextjs-project/components/
```

#### Use in Page
```typescript
// app/chart/page.tsx
import ThemisChart from '@/components/ThemisChart';

export default async function ChartPage() {
  // Fetch data from API route
  const data = await fetch('/api/chart-data?symbol=AAPL').then(r => r.json());
  
  return (
    <div>
      <h1>THEMIS Chart Viewer</h1>
      <ThemisChart 
        symbol="AAPL" 
        data={data} 
        height={600}
        showVolume={true}
        showMentions={true}
      />
    </div>
  );
}
```

#### Create API Route
```typescript
// app/api/chart-data/route.ts
import { NextResponse } from 'next/server';
import { ThemisMarketDataFetcher } from '@/lib/data-fetcher';

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const symbol = searchParams.get('symbol') || 'AAPL';
  
  const fetcher = new ThemisMarketDataFetcher();
  const data = await fetcher.merge_mentions_and_prices(symbol, 90);
  
  return NextResponse.json({
    symbol,
    prices: data.prices,
    mentions: data.mentions,
  });
}
```

### Features
- ✅ Full TypeScript support
- ✅ Custom styling
- ✅ Stats header (mentions, price change)
- ✅ Interactive tooltips
- ✅ Responsive design
- ✅ Production-ready

---

## Data Fetcher (All Options)

### Test Data Fetching
```bash
# Test database connection
python data_fetcher.py --trending

# Fetch specific symbol
python data_fetcher.py --symbol AAPL --days 90

# Test crypto
python data_fetcher.py --symbol BTC --days 30
```

### Expected Output
```
📊 Fetching data for AAPL...
✅ Fetched 90 days of price data
✅ Found 23 total mentions

📈 AAPL Data Preview:
         date  mention_count   close
0  2024-01-15              3  185.23
1  2024-01-16              0  186.45
...

🔥 Top Mention Days:
        date  mention_count   close
0  2024-02-01              8  191.23
1  2024-01-22              5  187.45
```

---

## TradingView Widget Examples

### View Static Examples
```bash
# Open in browser
open widget_embed_examples.html
# or
firefox widget_embed_examples.html
```

### Widget Types
1. **Advanced Chart** - Full chart with all tools (recommended)
2. **Symbol Overview** - Compact multi-symbol view
3. **Mini Chart** - Tiny embedded chart
4. **Ticker Tape** - Horizontal scrolling ticker
5. **Market Overview** - Grid heatmap view

---

## Architecture Comparison

| Feature | Streamlit | Lightweight Charts | React Component |
|---------|-----------|-------------------|----------------|
| **Setup Time** | 5 minutes | 10 minutes | 1-2 hours |
| **Customization** | Medium | High | Very High |
| **Production Ready** | No (prototyping) | No (demos) | Yes |
| **Auth/Users** | Basic | None | Full |
| **Real-time Updates** | Polling | None | WebSockets |
| **Mobile** | Responsive | Desktop only | Fully responsive |
| **Cost** | Free | Free | Free |

---

## Common Workflows

### 1. Quick Demo for Stakeholders
```bash
streamlit run themis_chart_streamlit.py
```
- Show trending symbols
- Load AAPL chart
- Demonstrate mention markers
- Export mention data CSV

### 2. Analyst Deep Dive
```bash
python lightweight_charts_python.py --symbol TSLA --days 180 --type price
```
- Open in browser
- Use TradingView tools to draw trendlines
- Correlate mention spikes with price action
- Export chart as PNG

### 3. Multi-Security Comparison
```bash
python lightweight_charts_python.py --type compare --compare BTC ETH SOL --days 90
```
- Compare crypto mention trends
- Identify leader/laggard
- Validate with price correlation

### 4. Production Platform
- Copy React component to Next.js app
- Create API routes for data fetching
- Add authentication (Supabase Auth)
- Deploy to Vercel

---

## Troubleshooting

### "No data found for symbol"
- Check if symbol exists in THEMIS database
- Run: `python data_fetcher.py --trending` to see available symbols
- Try different time range (--days 180)

### "Failed to initialize Supabase"
- Verify environment variables are set
- Check SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY
- Test connection: `python -c "from data_fetcher import ThemisMarketDataFetcher; ThemisMarketDataFetcher()"`

### "No market data available"
- Symbol might be delisted or invalid
- For crypto, use standard symbols: BTC, ETH, SOL (not BTC-USD)
- Try yfinance directly: `python -c "import yfinance as yf; print(yf.Ticker('AAPL').history(period='1mo'))"`

### TradingView widget not loading
- Check browser console for errors
- Verify symbol format: NASDAQ:AAPL (not just AAPL)
- For crypto: COINBASE:BTCUSD (not BTC-USD)
- Some exchanges: NYSE:, AMEX:, BINANCE:

---

## Next Steps

### Phase 1 (This Week)
- ✅ Test Streamlit app locally
- ✅ Verify data fetching works
- ✅ Demo to stakeholders

### Phase 2 (Next Week)
- [ ] Add more technical indicators (MACD, Bollinger Bands)
- [ ] Sentiment overlay (color mentions by theme sentiment)
- [ ] Multi-timeframe support (1H, 4H, 1D, 1W)
- [ ] Export to PDF reports

### Phase 3 (Next Month)
- [ ] Migrate to Next.js for production
- [ ] Add user authentication
- [ ] Create watchlists
- [ ] Real-time mention alerts
- [ ] API for third-party integrations

---

## Resources

### Documentation
- [TradingView Widgets](https://www.tradingview.com/widget/)
- [Lightweight Charts Docs](https://tradingview.github.io/lightweight-charts/)
- [Streamlit Docs](https://docs.streamlit.io/)
- [yfinance GitHub](https://github.com/ranaroussi/yfinance)

### Example Usage
```python
# Programmatic access
from data_fetcher import fetch_chart_data

# Get data
data = fetch_chart_data("AAPL", days_back=90)

# Analyze
mention_days = data[data['mention_count'] > 0]
correlation = data['mention_count'].corr(data['close'].pct_change())

print(f"Price/Mention Correlation: {correlation:.2f}")
```

### API Integration
```python
# For external platforms
import json
from data_fetcher import ThemisMarketDataFetcher

fetcher = ThemisMarketDataFetcher()
data = fetcher.merge_mentions_and_prices("TSLA", 30)

# Export as JSON
json_data = data.to_json(orient='records', date_format='iso')
print(json_data)
```

---

## 🎯 Recommended Path

**For MVP (Next 2 Weeks):**
1. Use Streamlit app (`themis_chart_streamlit.py`)
2. Test with 5-10 different symbols
3. Gather feedback from users
4. Iterate on features

**For Production (Months 2-3):**
1. Port to Next.js with React component
2. Add authentication & user profiles
3. Build API layer for external access
4. Deploy to Vercel/AWS

**Start here:**
```bash
streamlit run themis_chart_streamlit.py
```

🎉 **You're ready to visualize THEMIS investment signals!**
