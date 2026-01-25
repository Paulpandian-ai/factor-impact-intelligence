# 💰 Factor Impact Intelligence - Monetary Analyzer

**AI-Powered Stock Analysis Platform | CBS Technology Strategy Final Project**

Analyzes Federal Reserve policy, inflation trends, and Treasury yields to provide Buy/Hold/Sell recommendations for stocks.

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/YOUR_USERNAME/factor-impact-intelligence/blob/main/Factor_Impact_Intelligence_Colab.ipynb)
[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://YOUR_APP.streamlit.app)

---

## 🎯 What It Does

Democratizes institutional-grade monetary factor analysis:

- **Fed Rate Impact**: Analyzes how interest rate changes affect stock valuations
- **Inflation Analysis**: Tracks CPI trends and their market implications  
- **Treasury Yields**: Monitors the risk-free rate benchmark
- **Beta Adjustment**: Customizes impact based on stock volatility
- **Smart Scoring**: Generates 1-10 composite score → Buy/Hold/Sell signal

**Example Output:**
```
NVIDIA (NVDA) - Score: 7.5/10 - STRONG BUY
Beta: 1.75 (High-Beta Growth Stock)

Fed Rate: +0.5 (stable rates supportive)
Inflation: +1.2 (moderating, very positive)
Yields: +0.8 (falling, supportive for growth)

Recommendation: Moderating inflation provides supportive backdrop 
for high-beta growth stocks. Current monetary conditions favorable.
```

---

## 🚀 Quick Start (2 Options)

### Option A: Google Colab (No Setup)

1. Click the "Open in Colab" badge above
2. Get free FRED API key: [fred.stlouisfed.org](https://fred.stlouisfed.org/docs/api/api_key.html)
3. Run all cells
4. Enter API key and stock ticker
5. View results!

**Perfect for**: Testing, batch analysis, data export

### Option B: Streamlit Web App

1. Fork this repo
2. Deploy to [Streamlit Cloud](https://share.streamlit.io/) (free)
3. Add FRED API key to secrets
4. Access public URL

**Perfect for**: Sharing, presentation, always-on access

📖 **Full Instructions**: See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)

---

## 📊 Features

✅ **3 Monetary Factors Analyzed:**
- Federal Funds Rate (FRED API)
- CPI Inflation (FRED API)
- 10-Year Treasury Yield (FRED API)

✅ **Smart Recommendations:**
- Weighted composite scoring (-2 to +2 per factor)
- Beta-adjusted impact (growth stocks more sensitive)
- Confidence levels (High/Medium/Low)
- Plain-English reasoning

✅ **Visualizations:**
- Gauge charts for composite scores
- Historical trend charts
- Factor breakdown bars
- Interactive web interface

✅ **100% Free:**
- No paid APIs
- No local setup required
- Cloud-based (Colab + Streamlit)

---

## 🎓 Project Context

**Course**: Technology Strategy (CBS)  
**Timeline**: 30-day MVP development  
**Goal**: Democratize institutional-grade factor analysis

**This Module**: Week 1 - Monetary Factor Analysis  
**Future Modules**:
- Week 2: Supply Chain + Geopolitical Analysis
- Week 3: Correlation + Performance Metrics
- Week 4: Full Integration + Alternative Recommendations

---

## 📁 Repository Structure

```
factor-impact-intelligence/
├── streamlit_app.py                         # Web app
├── Factor_Impact_Intelligence_Colab.ipynb  # Colab notebook
├── requirements.txt                         # Dependencies
├── DEPLOYMENT_GUIDE.md                      # Setup instructions
├── README.md                                # This file
├── .gitignore                              # Git exclusions
└── .streamlit/
    └── secrets.toml.example                # API key template
```

---

## 🔧 Technology Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| **LLM** | Python | Universal, data-friendly |
| **Stock Data** | yfinance | Free Yahoo Finance API |
| **Economic Data** | FRED API | 800K+ free indicators |
| **Web UI** | Streamlit | Fastest Python web framework |
| **Viz** | Plotly | Interactive charts |
| **Hosting** | Colab + Streamlit Cloud | 100% free tier |

---

## 💡 How It Works

### Scoring Methodology

1. **Fetch Data**: Fed rates, CPI, yields (FRED API)
2. **Calculate Beta**: Stock volatility vs S&P 500 (yfinance)
3. **Score Factors**: -2 to +2 for each factor
4. **Adjust for Beta**: 
   - High-beta (>1.5): 30% amplification
   - Low-beta (<0.8): 30% dampening
5. **Weighted Composite**: 
   - Fed: 35%, Inflation: 35%, Yields: 30%
6. **Map to Signal**:
   - 7.5-10: Strong Buy
   - 6.5-7.4: Buy
   - 4.5-6.4: Hold
   - 2.5-4.4: Sell
   - 1.0-2.4: Strong Sell

### Example Calculation

```python
# NVDA with beta=1.75 (high-beta growth)
Fed Score: +0.5 (stable) × 1.3 (beta adj) = +0.65
Inflation: +1.0 (moderating) × 1.2 = +1.2
Yields: +1.0 (falling) × 1.3 = +1.3 (capped at weighted)

Weighted: (0.65×0.35) + (1.2×0.35) + (0.8×0.30) = 0.89
Composite: 5.5 + (0.89 × 2.25) = 7.5 → STRONG BUY
```

---

## 📈 Sample Results

| Ticker | Beta | Score | Signal | Key Factor |
|--------|------|-------|--------|------------|
| NVDA | 1.75 | 7.5 | STRONG BUY | Moderating inflation |
| AAPL | 1.21 | 6.8 | BUY | Stable rates |
| KO | 0.67 | 5.2 | HOLD | Defensive, less sensitivity |

---

## ⚠️ Disclaimer

**FOR EDUCATIONAL PURPOSES ONLY**

This tool is not investment advice. Past performance does not guarantee future results. Consult a qualified financial advisor before making investment decisions. Factor scores are model estimates and may not reflect actual market movements.

---

## 🤝 Contributing

This is a class project, but suggestions welcome:

1. Fork the repo
2. Create feature branch
3. Submit pull request

---

## 📄 License

MIT License - Free to use and modify with attribution

---

## 👤 Author

**Paul Balasubramanian**  
Columbia Business School  
Technology Strategy | Final Project

---

## 🔗 Links

- **Live Demo**: [Your Streamlit App URL]
- **Colab Notebook**: [Your Colab Link]
- **Documentation**: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- **FRED API**: https://fred.stlouisfed.org/

---

## ⭐ Show Your Support

If this helped your project:
- ⭐ Star this repo
- 📢 Share with classmates
- 💬 Provide feedback via Issues

---

**Version**: 1.0.0 | **Last Updated**: January 2026
