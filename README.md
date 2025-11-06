# 📈 TradingView Integration for THEMIS

## Overview
Connect THEMIS investment signals to TradingView charts to visualize when securities were mentioned alongside price action.

## Integration Options

### 🎯 Option 1: TradingView Widgets (FREE)
**Best for:** Quick MVP, embedded charts
**Cost:** Free
**Limitations:** Limited customization, TradingView branding

### 📊 Option 2: Lightweight Charts (FREE, Open Source)
**Best for:** Custom styling, mention markers
**Cost:** Free
**Library:** `lightweight-charts` by TradingView
**Limitations:** Manual data management

### 💎 Option 3: Advanced Charts Library (PAID)
**Best for:** Professional platform, custom indicators
**Cost:** $3,000/year
**Features:** Full customization, save layouts, custom studies

---

## 🚀 Quick Start Guide

### Option 1: Widget Embed (Fastest)
```html
<!-- Basic chart -->
<script src="https://s3.tradingview.com/tv.js"></script>
<script>
  new TradingView.widget({
    "symbol": "NASDAQ:AAPL",
    "interval": "D",
    "container_id": "tradingview_chart"
  });
</script>
```

### Option 2: Lightweight Charts (Recommended)
```bash
npm install lightweight-charts
# or
pip install lightweight-charts-python  # For Streamlit/Python
```

### Option 3: Advanced Charts
Requires license purchase from TradingView.

---

## 🎨 THEMIS Use Cases

### 1. **Mention Markers on Price Chart**
Show when a security was mentioned in YouTube videos:
- 📍 Blue arrow: Single mention
- 🔵 Large marker: Multiple mentions same day
- 📊 Tooltip: Channel name + video title

### 2. **Sentiment Overlay**
Color-code mentions by sentiment:
- 🟢 Bullish (positive themes)
- 🔴 Bearish (negative themes)
- 🟡 Neutral (informational)

### 3. **Theme Heatmap**
Show which investment themes are trending alongside price:
- Volume bar colors = theme intensity
- Annotations = major theme shifts

### 4. **Multi-Security Comparison**
Compare mention frequency across securities:
- Subplot: Mention count timeline
- Main chart: Price overlay

---

## 📁 Files in This Directory

- `widget_embed_examples.html` - Static HTML widget examples
- `lightweight_charts_python.py` - Python/Streamlit integration
- `lightweight_charts_react.tsx` - React/Next.js component
- `themis_chart_streamlit.py` - Full Streamlit app with THEMIS data
- `data_fetcher.py` - Fetch THEMIS mentions + market prices
- `chart_config.json` - Reusable chart configurations

---

## 🔌 Data Flow

```
┌─────────────────────────────────────────────────────┐
│ THEMIS Database (Supabase)                          │
│  - securities (mentions + timestamps)               │
│  - investment_themes (sentiment)                    │
└─────────────┬───────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────┐
│ Data Fetcher (Python)                               │
│  - Aggregate mentions by date                       │
│  - Fetch market prices (yfinance/Alpha Vantage)     │
│  - Merge into chart-ready format                    │
└─────────────┬───────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────┐
│ Chart Component                                      │
│  - Render candlestick/line chart                    │
│  - Add mention markers                              │
│  - Interactive tooltips                             │
└─────────────────────────────────────────────────────┘
```

---

## 🎯 Next Steps
1. Choose integration option (widget vs lightweight)
2. Fetch THEMIS mention data
3. Combine with market price data
4. Render chart with markers
