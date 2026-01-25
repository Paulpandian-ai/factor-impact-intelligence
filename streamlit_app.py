"""
Factor Impact Intelligence - Streamlit Web App
For deployment on Streamlit Cloud

Author: Paul Balasubramanian
Project: Technology Strategy Final Project
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


# Page configuration
st.set_page_config(
    page_title="Factor Impact Intelligence",
    page_icon="💰",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem 0;
    }
    .buy-signal {
        color: #00cc00;
        font-weight: bold;
        font-size: 1.8rem;
    }
    .sell-signal {
        color: #ff0000;
        font-weight: bold;
        font-size: 1.8rem;
    }
    .hold-signal {
        color: #ff9900;
        font-weight: bold;
        font-size: 1.8rem;
    }
    .disclaimer {
        background-color: #fff3cd;
        border: 1px solid #ffc107;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)


class MonetaryFactorAnalyzer:
    """Analyzes monetary factors and provides stock recommendations"""
    
    def __init__(self, fred_api_key: str):
        self.fred = Fred(api_key=fred_api_key)
        self.weights = {
            'fed_rate': 0.35,
            'inflation': 0.35,
            'treasury_yield': 0.30
        }
    
    def get_stock_data(self, ticker: str):
        try:
            stock = yf.Ticker(ticker)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365)
            hist = stock.history(start=start_date, end=end_date)
            if hist.empty:
                return None, None
            return hist, stock.info
        except:
            return None, None
    
    def calculate_stock_beta(self, stock_data, info):
        try:
            if 'beta' in info and info['beta']:
                return float(info['beta'])
            stock_returns = stock_data['Close'].pct_change().dropna()
            spy = yf.Ticker('SPY')
            spy_hist = spy.history(start=stock_data.index[0], end=stock_data.index[-1])
            spy_returns = spy_hist['Close'].pct_change().dropna()
            aligned_data = pd.DataFrame({'stock': stock_returns, 'market': spy_returns}).dropna()
            if len(aligned_data) < 30:
                return 1.0
            cov = aligned_data.cov().loc['stock', 'market']
            var = aligned_data['market'].var()
            return cov / var
        except:
            return 1.0
    
    def get_fed_funds_rate(self):
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365)
            fed_rate = self.fred.get_series('FEDFUNDS', observation_start=start_date, observation_end=end_date)
            if fed_rate.empty:
                return None
            current_rate = fed_rate.iloc[-1]
            three_months_ago = fed_rate.iloc[-4] if len(fed_rate) >= 4 else fed_rate.iloc[0]
            change_3m = current_rate - three_months_ago
            
            if change_3m > 0.25:
                trend = "aggressive_tightening"
            elif change_3m > 0:
                trend = "tightening"
            elif change_3m < -0.25:
                trend = "aggressive_easing"
            elif change_3m < 0:
                trend = "easing"
            else:
                trend = "stable"
            
            return {'current_rate': current_rate, 'change_3m': change_3m, 'trend': trend, 'data': fed_rate}
        except:
            return None
    
    def get_inflation_data(self):
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365)
            cpi = self.fred.get_series('CPIAUCSL', observation_start=start_date, observation_end=end_date)
            if cpi.empty or len(cpi) < 12:
                return None
            current_cpi = cpi.iloc[-1]
            year_ago_cpi = cpi.iloc[-13] if len(cpi) >= 13 else cpi.iloc[0]
            yoy_inflation = ((current_cpi - year_ago_cpi) / year_ago_cpi) * 100
            
            if yoy_inflation > 4.0:
                trend = "high_inflation"
            elif yoy_inflation > 2.5:
                trend = "elevated_inflation"
            elif yoy_inflation >= 1.5:
                trend = "target_range"
            else:
                trend = "low_inflation"
            
            return {'yoy_inflation': yoy_inflation, 'trend': trend, 'data': cpi}
        except:
            return None
    
    def get_treasury_yield(self):
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365)
            treasury_yield = self.fred.get_series('DGS10', observation_start=start_date, observation_end=end_date)
            treasury_yield = treasury_yield.dropna()
            if treasury_yield.empty:
                return None
            current_yield = treasury_yield.iloc[-1]
            month_ago = treasury_yield.iloc[-22] if len(treasury_yield) >= 22 else treasury_yield.iloc[0]
            change_1m = current_yield - month_ago
            
            if change_1m > 0.5:
                trend = "rapid_rise"
            elif change_1m > 0.1:
                trend = "rising"
            elif change_1m < -0.5:
                trend = "rapid_fall"
            elif change_1m < -0.1:
                trend = "falling"
            else:
                trend = "stable"
            
            return {'current_yield': current_yield, 'change_1m': change_1m, 'trend': trend, 'data': treasury_yield}
        except:
            return None
    
    def score_fed_rate_impact(self, fed_data, stock_beta):
        if not fed_data:
            return 0, "Unable to assess Fed rate impact"
        
        trend_scores = {
            "aggressive_tightening": -2.0, "tightening": -1.0,
            "aggressive_easing": 2.0, "easing": 1.0, "stable": 0.0
        }
        base_score = trend_scores[fed_data['trend']]
        
        if stock_beta > 1.5:
            multiplier = 1.3
        elif stock_beta > 1.2:
            multiplier = 1.15
        elif stock_beta < 0.8:
            multiplier = 0.7
        else:
            multiplier = 1.0
        
        final_score = max(-2.0, min(2.0, base_score * multiplier))
        reasoning = f"Fed Funds Rate: {fed_data['current_rate']:.2f}% ({fed_data['change_3m']:+.2f}% 3M change). "
        
        if final_score < -1:
            reasoning += "VERY NEGATIVE - Rate hikes compress valuations"
        elif final_score > 1:
            reasoning += "VERY POSITIVE - Rate cuts boost growth"
        else:
            reasoning += "Neutral impact"
        
        return final_score, reasoning
    
    def score_inflation_impact(self, inflation_data, stock_beta):
        if not inflation_data:
            return 0, "Unable to assess inflation impact"
        
        trend_scores = {
            "high_inflation": -1.5, "elevated_inflation": -0.5,
            "target_range": 1.0, "low_inflation": 0.0
        }
        base_score = trend_scores[inflation_data['trend']]
        multiplier = 1.2 if stock_beta > 1.5 else 1.0
        final_score = max(-2.0, min(2.0, base_score * multiplier))
        
        reasoning = f"CPI: {inflation_data['yoy_inflation']:.2f}% YoY. "
        if final_score < -1:
            reasoning += "VERY NEGATIVE - High inflation forces tightening"
        elif final_score > 1:
            reasoning += "VERY POSITIVE - Cooling inflation"
        else:
            reasoning += "Moderate impact"
        
        return final_score, reasoning
    
    def score_treasury_yield_impact(self, yield_data, stock_beta):
        if not yield_data:
            return 0, "Unable to assess yield impact"
        
        trend_scores = {
            "rapid_rise": -2.0, "rising": -1.0,
            "rapid_fall": 2.0, "falling": 1.0, "stable": 0.0
        }
        base_score = trend_scores[yield_data['trend']]
        multiplier = 1.3 if stock_beta > 1.5 else 1.0
        final_score = max(-2.0, min(2.0, base_score * multiplier))
        
        reasoning = f"10Y Yield: {yield_data['current_yield']:.2f}%. "
        if final_score < -1:
            reasoning += "VERY NEGATIVE - Rising yields compress valuations"
        elif final_score > 1:
            reasoning += "VERY POSITIVE - Falling yields support growth"
        else:
            reasoning += "Moderate impact"
        
        return final_score, reasoning
    
    def calculate_composite_score(self, fed_score, inflation_score, yield_score):
        weighted = (fed_score * 0.35 + inflation_score * 0.35 + yield_score * 0.30)
        return round(5.5 + (weighted * 2.25), 1)
    
    def get_recommendation_signal(self, score):
        if score >= 7.5:
            return "STRONG BUY", "High"
        elif score >= 6.5:
            return "BUY", "Medium-High"
        elif score >= 5.5:
            return "HOLD (Lean Buy)", "Medium"
        elif score >= 4.5:
            return "HOLD", "Medium"
        elif score >= 3.5:
            return "HOLD (Lean Sell)", "Medium"
        elif score >= 2.5:
            return "SELL", "Medium-High"
        else:
            return "STRONG SELL", "High"
    
    def analyze_ticker(self, ticker):
        stock_data, stock_info = self.get_stock_data(ticker)
        if stock_data is None:
            return {'error': f"Unable to fetch data for {ticker}", 'success': False}
        
        stock_beta = self.calculate_stock_beta(stock_data, stock_info)
        fed_data = self.get_fed_funds_rate()
        inflation_data = self.get_inflation_data()
        yield_data = self.get_treasury_yield()
        
        fed_score, fed_reasoning = self.score_fed_rate_impact(fed_data, stock_beta)
        inflation_score, inflation_reasoning = self.score_inflation_impact(inflation_data, stock_beta)
        yield_score, yield_reasoning = self.score_treasury_yield_impact(yield_data, stock_beta)
        
        composite_score = self.calculate_composite_score(fed_score, inflation_score, yield_score)
        signal, confidence = self.get_recommendation_signal(composite_score)
        
        return {
            'success': True,
            'ticker': ticker.upper(),
            'stock_beta': stock_beta,
            'composite_score': composite_score,
            'recommendation': signal,
            'confidence': confidence,
            'factors': {
                'fed_rate': {'score': fed_score, 'reasoning': fed_reasoning, 'data': fed_data},
                'inflation': {'score': inflation_score, 'reasoning': inflation_reasoning, 'data': inflation_data},
                'treasury_yield': {'score': yield_score, 'reasoning': yield_reasoning, 'data': yield_data}
            }
        }


# Main App
st.markdown('<div class="main-header">💰 Factor Impact Intelligence</div>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center; color: #666;">Monetary Factor Analysis Platform</p>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Get API key from Streamlit secrets or user input
    if 'fred_api_key' in st.secrets:
        fred_api_key = st.secrets['fred_api_key']
        st.success("✅ API key loaded from secrets")
    else:
        st.warning("⚠️ Add API key to Streamlit secrets")
        fred_api_key = st.text_input("FRED API Key", type="password", 
                                     help="Get free key at fred.stlouisfed.org")
    
    st.markdown("---")
    st.markdown("""
    ### About
    This tool analyzes:
    - 🏦 Fed Policy (Interest Rates)
    - 📊 Inflation Trends (CPI)
    - 📈 Treasury Yields (10-Year)
    
    Generates Buy/Hold/Sell signals based on monetary conditions.
    """)
    
    st.markdown("---")
    st.caption("CBS Technology Strategy | Final Project")

# Main content
if not fred_api_key:
    st.info("👈 Please enter your FRED API key in the sidebar to begin")
    st.markdown("""
    ### Get Started
    1. Visit [fred.stlouisfed.org](https://fred.stlouisfed.org/docs/api/api_key.html)
    2. Create free account
    3. Request API key (instant)
    4. Enter in sidebar
    """)
else:
    analyzer = MonetaryFactorAnalyzer(fred_api_key=fred_api_key)
    
    # Stock input
    col1, col2 = st.columns([3, 1])
    with col1:
        ticker = st.text_input("Enter Stock Ticker", value="NVDA", 
                              help="E.g., NVDA, AAPL, MSFT").upper()
    with col2:
        st.write("")
        st.write("")
        analyze_button = st.button("📊 Analyze", type="primary", use_container_width=True)
    
    # Analyze
    if analyze_button and ticker:
        with st.spinner(f"Analyzing {ticker}..."):
            result = analyzer.analyze_ticker(ticker)
        
        if not result['success']:
            st.error(f"❌ {result.get('error', 'Unknown error')}")
        else:
            # Metrics
            st.markdown("---")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Composite Score", f"{result['composite_score']}/10")
            
            with col2:
                signal = result['recommendation']
                if 'BUY' in signal:
                    st.markdown(f'<div class="buy-signal">{signal}</div>', unsafe_allow_html=True)
                elif 'SELL' in signal:
                    st.markdown(f'<div class="sell-signal">{signal}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="hold-signal">{signal}</div>', unsafe_allow_html=True)
                st.caption("Recommendation")
            
            with col3:
                st.metric("Confidence", result['confidence'])
            
            with col4:
                beta = result['stock_beta']
                beta_type = "High-Beta" if beta > 1.5 else "Growth" if beta > 1.2 else "Market" if beta > 0.8 else "Defensive"
                st.metric("Beta", f"{beta:.2f}", help=f"{beta_type} stock")
            
            # Gauge chart
            st.markdown("---")
            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=result['composite_score'],
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "Monetary Factor Score"},
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
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
            
            # Factor breakdown
            st.markdown("---")
            st.subheader("📋 Factor Breakdown")
            
            factors = result['factors']
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("#### 🏦 Fed Rate")
                st.metric("Score", f"{factors['fed_rate']['score']:+.1f}/2.0")
                st.caption(factors['fed_rate']['reasoning'])
                if factors['fed_rate']['data']:
                    st.info(f"Current: **{factors['fed_rate']['data']['current_rate']:.2f}%**")
            
            with col2:
                st.markdown("#### 📊 Inflation")
                st.metric("Score", f"{factors['inflation']['score']:+.1f}/2.0")
                st.caption(factors['inflation']['reasoning'])
                if factors['inflation']['data']:
                    st.info(f"YoY: **{factors['inflation']['data']['yoy_inflation']:.2f}%**")
            
            with col3:
                st.markdown("#### 📈 Treasury Yield")
                st.metric("Score", f"{factors['treasury_yield']['score']:+.1f}/2.0")
                st.caption(factors['treasury_yield']['reasoning'])
                if factors['treasury_yield']['data']:
                    st.info(f"Current: **{factors['treasury_yield']['data']['current_yield']:.2f}%**")
            
            # Historical charts
            st.markdown("---")
            st.subheader("📈 Historical Indicators")
            
            tab1, tab2, tab3 = st.tabs(["Fed Funds", "CPI", "10Y Treasury"])
            
            with tab1:
                if factors['fed_rate']['data']:
                    st.line_chart(factors['fed_rate']['data'])
            
            with tab2:
                if factors['inflation']['data']:
                    st.line_chart(factors['inflation']['data'])
            
            with tab3:
                if factors['treasury_yield']['data']:
                    st.line_chart(factors['treasury_yield']['data'])

# Disclaimer
st.markdown("---")
st.markdown("""
<div class="disclaimer">
    <strong>⚠️ DISCLAIMER</strong><br>
    For educational purposes only. NOT investment advice. 
    Consult a qualified financial advisor before making investment decisions.
</div>
""", unsafe_allow_html=True)
