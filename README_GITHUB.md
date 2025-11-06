# 📈 THEMIS TradingView Charts

Interactive charts visualizing YouTube investment intelligence signals on price charts.

## 🚀 Quick Deploy to Streamlit Cloud

### 1. Fork/Clone This Repo
Already done if you're reading this! ✅

### 2. Deploy to Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click **"New app"**
3. Select this repository: `DogginitAN/themis-charts`
4. Main file path: `themis_chart_streamlit.py`
5. Click **"Advanced settings"** and add secrets:
   ```toml
   SUPABASE_URL = "your_supabase_project_url"
   SUPABASE_SERVICE_ROLE_KEY = "your_service_role_key"
   ```
6. Click **"Deploy"**

### 3. Access Your App
You'll get a URL like: `https://themis-charts.streamlit.app`

---

## 🎯 What This Does

- **Fetch Security Mentions** - Queries THEMIS database for YouTube mentions
- **Get Market Data** - Pulls historical prices via yfinance
- **Visualize** - Overlays mention markers on TradingView charts
- **Analyze** - Correlate YouTube buzz with price movements

---

## 📊 Features

✅ TradingView widget integration (free)  
✅ Custom interactive charts with mention markers  
✅ Trending securities sidebar  
✅ Mention timeline bar charts  
✅ Detailed context (videos, channels, themes)  
✅ CSV export  

---

## 🛠️ Local Development

### Prerequisites
- Python 3.9+
- Supabase account with THEMIS data

### Setup
```bash
# Clone repo
git clone https://github.com/DogginitAN/themis-charts.git
cd themis-charts

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export SUPABASE_URL="your_supabase_url"
export SUPABASE_SERVICE_ROLE_KEY="your_service_role_key"

# Run app
streamlit run themis_chart_streamlit.py
```

App opens at: http://localhost:8501

---

## 📁 Project Structure

```
themis-charts/
├── themis_chart_streamlit.py    # Main Streamlit app ⭐
├── data_fetcher.py               # THEMIS + market data integration
├── lightweight_charts_python.py  # Standalone Python charts
├── ThemisChart.tsx               # React component (for Next.js)
├── widget_embed_examples.html    # TradingView widget demos
├── requirements.txt              # Python dependencies
├── QUICK_START.md                # Detailed setup guide
└── IMPLEMENTATION_SUMMARY.md     # Architecture docs
```

---

## 🎨 Usage Examples

### View Trending Securities
```bash
python data_fetcher.py --trending
```

### Fetch Specific Symbol
```bash
python data_fetcher.py --symbol AAPL --days 90
```

### Run Standalone Chart
```bash
python lightweight_charts_python.py --symbol BTC --type price
```

### Compare Multiple Securities
```bash
python lightweight_charts_python.py --type compare --compare AAPL TSLA NVDA
```

---

## 🔧 Configuration

### Streamlit Secrets (Cloud Deployment)
Add in Streamlit Cloud dashboard under "Advanced settings":

```toml
SUPABASE_URL = "https://xxxxx.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### Local Development (.env file)
```bash
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## 📖 Documentation

- **[QUICK_START.md](QUICK_START.md)** - Detailed setup & deployment guide
- **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** - Architecture & technical details
- **[README.md](README.md)** - Integration options overview

---

## 🚀 Deployment Options

| Option | Time | Cost | Best For |
|--------|------|------|----------|
| **Streamlit Cloud** | 1 hour | Free | MVP, demos, internal tools |
| **Docker/VPS** | 1 day | $5/mo | Custom domain, full control |
| **Next.js (Vercel)** | 2-4 weeks | Free | Production SaaS |

See [QUICK_START.md](QUICK_START.md) for detailed comparison.

---

## 🎯 Roadmap

### ✅ Phase 1 - MVP (Complete)
- Streamlit web app
- TradingView integration
- THEMIS data pipeline
- Market data fetching

### 🔄 Phase 2 - Enhancement (In Progress)
- [ ] Sentiment overlay (color mentions by theme)
- [ ] Multi-timeframe support (1H, 1D, 1W)
- [ ] More technical indicators
- [ ] PDF export

### 🔮 Phase 3 - Production (Planned)
- [ ] Next.js migration
- [ ] User authentication
- [ ] Watchlists & alerts
- [ ] API for external integrations
- [ ] Mobile app

---

## 📊 Tech Stack

- **Frontend:** Streamlit (Python web framework)
- **Charts:** TradingView widgets + Plotly
- **Database:** Supabase (PostgreSQL)
- **Market Data:** yfinance (Yahoo Finance)
- **Deployment:** Streamlit Cloud (free tier)

---

## 🤝 Contributing

This is a THEMIS platform component. For questions or contributions:

1. Open an issue
2. Submit a pull request
3. Contact: [your-email@example.com]

---

## 📝 License

MIT License - see LICENSE file for details

---

## 🙏 Acknowledgments

- **TradingView** - Chart widgets & Lightweight Charts library
- **Streamlit** - Python web framework
- **yfinance** - Market data API
- **Supabase** - Database & authentication

---

## 🔗 Links

- **Live Demo:** [themis-charts.streamlit.app](https://themis-charts.streamlit.app) (coming soon)
- **Documentation:** [Full docs](QUICK_START.md)
- **THEMIS Platform:** [Main repo](https://github.com/DogginitAN/themis)

---

**Built with ❤️ for the THEMIS Investment Intelligence Platform**
