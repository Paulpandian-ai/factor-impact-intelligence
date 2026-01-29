"""
Factor Impact Intelligence - Multi-Module Analysis Platform
Modules: Monetary + Company Performance
"""

import streamlit as st
import yfinance as yf
from fredapi import Fred
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.graph_objects as go
import warnings
warnings.filterwarnings('ignore')

# Import company analyzer
from company_analyzer import CompanyPerformanceAnalyzer

st.set_page_config(page_title="Factor Impact Intelligence", page_icon="💰", layout="wide")

# Header
st.markdown("# 💰 Factor Impact Intelligence")
st.markdown("### Multi-Factor Stock Analysis Platform")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    
    if 'fred_api_key' in st.secrets:
        fred_api_key = st.secrets['fred_api_key']
        st.success("✅ API key loaded")
    else:
        fred_api_key = st.text_input("FRED API Key", type="password", 
                                     help="Get free key at fred.stlouisfed.org")
    
    st.markdown("---")
    st.markdown("""
    ### Modules Active
    - ✅ Module 0: Monetary Factors
    - ✅ Module 1: Company Performance
    - 🔲 Module 2: Supplier Analysis
    - 🔲 Module 3: Customer Analysis
    - 🔲 Module 4: Competitor Analysis
    - 🔲 Module 5: Macro Factors
    - 🔲 Module 6: Correlation Analysis
    - 🔲 Module 7: Master Agent
    """)


class MonetaryFactorAnalyzer:
    """Analyzes monetary factors"""
    
    def __init__(self, fred_api_key):
        self.fred = Fred(api_key=fred_api_key)
    
    def get_stock_data(self, ticker):
        try:
            stock = yf.Ticker(ticker)
            end = datetime.now()
            start = end - timedelta(days=365)
            hist = stock.history(start=start, end=end)
            if hist.empty:
                return None, None
            return hist, stock.info
        except:
            return None, None
    
    def calculate_beta(self, stock_data, info):
        try:
            if 'beta' in info and info['beta']:
                return float(info['beta'])
            returns = stock_data['Close'].pct_change().dropna()
            spy = yf.Ticker('SPY')
            spy_hist = spy.history(start=stock_data.index[0], end=stock_data.index[-1])
            spy_returns = spy_hist['Close'].pct_change().dropna()
            aligned = pd.DataFrame({'stock': returns, 'market': spy_returns}).dropna()
            if len(aligned) < 30:
                return 1.0
            return aligned.cov().loc['stock', 'market'] / aligned['market'].var()
        except:
            return 1.0
    
    def get_fed_rate(self):
        try:
            end = datetime.now()
            start = end - timedelta(days=365)
            data = self.fred.get_series('FEDFUNDS', observation_start=start, observation_end=end)
            if data.empty:
                return None
            current = data.iloc[-1]
            prev = data.iloc[-4] if len(data) >= 4 else data.iloc[0]
            change = current - prev
            if change > 0.25:
                trend = "aggressive_tightening"
            elif change > 0:
                trend = "tightening"
            elif change < -0.25:
                trend = "aggressive_easing"
            elif change < 0:
                trend = "easing"
            else:
                trend = "stable"
            return {'current': current, 'change': change, 'trend': trend}
        except:
            return None
    
    def get_inflation(self):
        try:
            end = datetime.now()
            start = end - timedelta(days=365)
            cpi = self.fred.get_series('CPIAUCSL', observation_start=start, observation_end=end)
            if cpi.empty or len(cpi) < 12:
                return None
            current = cpi.iloc[-1]
            prev = cpi.iloc[-13] if len(cpi) >= 13 else cpi.iloc[0]
            yoy = ((current - prev) / prev) * 100
            if yoy > 4.0:
                trend = "high"
            elif yoy > 2.5:
                trend = "elevated"
            elif yoy >= 1.5:
                trend = "target"
            else:
                trend = "low"
            return {'yoy': yoy, 'trend': trend}
        except:
            return None
    
    def get_yield(self):
        try:
            end = datetime.now()
            start = end - timedelta(days=365)
            data = self.fred.get_series('DGS10', observation_start=start, observation_end=end).dropna()
            if data.empty:
                return None
            current = data.iloc[-1]
            prev = data.iloc[-22] if len(data) >= 22 else data.iloc[0]
            change = current - prev
            if change > 0.5:
                trend = "rapid_rise"
            elif change > 0.1:
                trend = "rising"
            elif change < -0.5:
                trend = "rapid_fall"
            elif change < -0.1:
                trend = "falling"
            else:
                trend = "stable"
            return {'current': current, 'change': change, 'trend': trend}
        except:
            return None
    
    def analyze(self, ticker):
        stock_data, info = self.get_stock_data(ticker)
        if stock_data is None:
            return {'success': False, 'error': 'No data'}
        
        beta = self.calculate_beta(stock_data, info)
        fed_data = self.get_fed_rate()
        inf_data = self.get_inflation()
        yld_data = self.get_yield()
        
        fed_scores = {"aggressive_tightening": -2.0, "tightening": -1.0, "aggressive_easing": 2.0, "easing": 1.0, "stable": 0.0}
        fed_score = fed_scores.get(fed_data['trend'], 0) if fed_data else 0
        
        inf_scores = {"high": -1.5, "elevated": -0.5, "target": 1.0, "low": 0.0}
        inf_score = inf_scores.get(inf_data['trend'], 0) if inf_data else 0
        
        yld_scores = {"rapid_rise": -2.0, "rising": -1.0, "rapid_fall": 2.0, "falling": 1.0, "stable": 0.0}
        yld_score = yld_scores.get(yld_data['trend'], 0) if yld_data else 0
        
        if beta > 1.5:
            fed_score = max(-2.0, min(2.0, fed_score * 1.3))
            inf_score = max(-2.0, min(2.0, inf_score * 1.2))
            yld_score = max(-2.0, min(2.0, yld_score * 1.3))
        
        weighted = (fed_score * 0.35) + (inf_score * 0.35) + (yld_score * 0.30)
        composite = round(5.5 + (weighted * 2.25), 1)
        
        if composite >= 7.5:
            signal = "STRONG BUY"
        elif composite >= 6.5:
            signal = "BUY"
        elif composite >= 5.5:
            signal = "HOLD (Lean Buy)"
        elif composite >= 4.5:
            signal = "HOLD"
        elif composite >= 3.5:
            signal = "HOLD (Lean Sell)"
        elif composite >= 2.5:
            signal = "SELL"
        else:
            signal = "STRONG SELL"
        
        return {
            'success': True, 'ticker': ticker.upper(), 'score': composite,
            'signal': signal, 'beta': beta, 'fed': fed_data, 'inf': inf_data,
            'yld': yld_data, 'fed_score': fed_score, 'inf_score': inf_score, 'yld_score': yld_score
        }


# Main app
if not fred_api_key:
    st.info("👈 Enter your FRED API key in the sidebar")
    st.stop()

# Stock input
col1, col2 = st.columns([3, 1])
with col1:
    ticker = st.text_input("Stock Ticker", value="NVDA", help="Enter stock symbol (e.g., NVDA, AAPL, MSFT)").upper()
with col2:
    st.write("")
    st.write("")
    analyze_btn = st.button("📊 Analyze All Modules", type="primary")

if analyze_btn and ticker:
    # Create tabs for different modules
    tab1, tab2, tab3 = st.tabs(["📊 Summary", "💰 Monetary Analysis", "📄 Company Analysis"])
    
    with st.spinner(f"Analyzing {ticker} across all modules..."):
        # Run both analyses
        monetary_analyzer = MonetaryFactorAnalyzer(fred_api_key=fred_api_key)
        company_analyzer = CompanyPerformanceAnalyzer()
        
        monetary_result = monetary_analyzer.analyze(ticker)
        company_result = company_analyzer.analyze(ticker, verbose=False)
    
    # TAB 1: Summary
    with tab1:
        st.markdown(f"## {ticker} - Multi-Module Analysis")
        
        if monetary_result['success'] and company_result['success']:
            # Combined score (simple average for now)
            combined_score = round((monetary_result['score'] * 0.5 + company_result['score'] * 0.5), 1)
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Combined Score", f"{combined_score}/10")
            with col2:
                st.metric("Signal", company_result['signal'])
    
    # Add data timestamp
    if company_result.get('data_date'):
        st.caption(f"📅 Data from: {company_result['data_date']}")
        st.caption(f"🕐 Age: {company_result['data_age_days']} days")
        
        if company_result.get('is_stale'):
            st.warning("⚠️ Data is >6 months old - use caution")
            with col3:
                st.metric("Company Score", f"{company_result['score']}/10")
            with col4:
                st.metric("Beta", f"{monetary_result['beta']:.2f}")
            
            # Gauge chart
            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=combined_score,
                title={'text': f"{ticker} Overall Score"},
                gauge={
                    'axis': {'range': [0, 10]},
                    'bar': {'color': "darkblue"},
                    'steps': [
                        {'range': [0, 3], 'color': "lightcoral"},
                        {'range': [3, 7], 'color': "lightyellow"},
                        {'range': [7, 10], 'color': "lightgreen"}
                    ]
                }
            ))
            st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("### 📊 Module Breakdown")
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 💰 Monetary Factors")
                st.metric("Score", f"{monetary_result['score']}/10")
                st.write(f"**Signal:** {monetary_result['signal']}")
                if monetary_result['fed']:
                    st.write(f"Fed Rate: {monetary_result['fed']['current']:.2f}%")
                if monetary_result['inf']:
                    st.write(f"Inflation: {monetary_result['inf']['yoy']:.2f}%")
            
            with col2:
                st.markdown("#### 📄 Company Performance")
                st.metric("Score", f"{company_result['score']}/10")
                st.write(f"**Signal:** {company_result['signal']}")
        else:
            st.error("Unable to complete analysis")
    
    # TAB 2: Monetary Analysis
    with tab2:
        if monetary_result['success']:
            st.markdown(f"## 💰 Monetary Factor Analysis: {ticker}")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Score", f"{monetary_result['score']}/10")
            with col2:
                st.metric("Signal", monetary_result['signal'])
            with col3:
                st.metric("Beta", f"{monetary_result['beta']:.2f}")
            
            st.markdown("### Factor Scores")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("#### 🏦 Fed Rate")
                st.metric("Score", f"{monetary_result['fed_score']:+.1f}/2.0")
                if monetary_result['fed']:
                    st.info(f"Current: {monetary_result['fed']['current']:.2f}%")
            
            with col2:
                st.markdown("#### 📊 Inflation")
                st.metric("Score", f"{monetary_result['inf_score']:+.1f}/2.0")
                if monetary_result['inf']:
                    st.info(f"YoY: {monetary_result['inf']['yoy']:.2f}%")
            
            with col3:
                st.markdown("#### 📈 Yields")
                st.metric("Score", f"{monetary_result['yld_score']:+.1f}/2.0")
                if monetary_result['yld']:
                    st.info(f"10Y: {monetary_result['yld']['current']:.2f}%")
    
    # TAB 3: Company Analysis
    with tab3:
        if company_result['success']:
            st.markdown(f"## 📄 Company Performance Analysis: {ticker}")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Company Score", f"{company_result['score']}/10")
            with col2:
                st.metric("Signal", company_result['signal'])
            
            st.markdown("### Performance Factors")
            
            factors = company_result['factors']
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("#### 📊 Revenue Growth")
                st.metric("Score", f"{factors['revenue_growth']['score']:+.1f}/2.0")
                st.caption(factors['revenue_growth']['reasoning'])
                
                st.markdown("#### 💰 Profitability")
                st.metric("Score", f"{factors['profitability']['score']:+.1f}/2.0")
                st.caption(factors['profitability']['reasoning'])
            
            with col2:
                st.markdown("#### 📈 Margins")
                st.metric("Score", f"{factors['margins']['score']:+.1f}/2.0")
                st.caption(factors['margins']['reasoning'])
                
                st.markdown("#### 🏥 Financial Health")
                st.metric("Score", f"{factors['financial_health']['score']:+.1f}/2.0")
                st.caption(factors['financial_health']['reasoning'])
            
            with col3:
                st.markdown("#### 🎯 Guidance")
                st.metric("Score", f"{factors['guidance']['score']:+.1f}/2.0")
                st.caption(factors['guidance']['reasoning'])
        else:
            st.error(f"Error: {company_result.get('error', 'Unknown error')}")

# Disclaimer
st.markdown("---")
st.markdown("""
<div style="background-color: #fff3cd; padding: 1rem; border-radius: 0.5rem;">
    <strong>⚠️ DISCLAIMER</strong><br>
    For educational purposes only. NOT investment advice. 
    Consult a qualified financial advisor before making investment decisions.
</div>
""", unsafe_allow_html=True)
