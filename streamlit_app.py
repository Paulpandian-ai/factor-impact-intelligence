"""
Factor Impact Intelligence - Complete Platform
Modules: Monetary + Company + Suppliers + Customers + Macro Factors
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

# Import analyzers
from company_analyzer import CompanyPerformanceAnalyzer
from supplier_analyzer import SupplierAnalyzer
from customer_analyzer import CustomerAnalyzer
from macro_analyzer import MacroFactorAnalyzer

st.set_page_config(page_title="Factor Impact Intelligence", page_icon="💰", layout="wide")

# Header
st.markdown("# 💰 Factor Impact Intelligence")
st.markdown("### Complete Multi-Factor Stock Analysis Platform")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # FRED API Key
    if 'fred_api_key' in st.secrets:
        fred_api_key = st.secrets['fred_api_key']
        st.success("✅ FRED API loaded")
    else:
        fred_api_key = st.text_input("FRED API Key", type="password")
    
    st.markdown("---")
    
    # Anthropic API Key
    if 'ANTHROPIC_API_KEY' in st.secrets:
        anthropic_api_key = st.secrets['ANTHROPIC_API_KEY']
        st.success("✅ Anthropic API loaded")
    else:
        anthropic_api_key = st.text_input("Anthropic API Key", type="password")
    
    st.markdown("---")
    st.markdown("""
    ### 📊 Active Modules (5)
    - ✅ Module 0: Monetary Factors
    - ✅ Module 1: Company Performance
    - ✅ Module 2: Supplier Analysis
    - ✅ Module 3: Customer Analysis
    - ✅ Module 5: Macro Factors
    
    ### 🔜 Coming Soon
    - Module 8: Analyst Critique
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
        else:
            signal = "HOLD/SELL"
        
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
    ticker = st.text_input("Stock Ticker", value="NVDA", help="Enter stock symbol").upper()
with col2:
    st.write("")
    st.write("")
    analyze_btn = st.button("📊 Analyze All Modules", type="primary")

if analyze_btn and ticker:
    # Create tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Summary", "💰 Monetary", "📄 Company", 
        "🏭 Suppliers", "👥 Customers", "🌍 Macro"
    ])
    
    with st.spinner(f"Analyzing {ticker} across all modules (90-120 seconds)..."):
        # Monetary Analysis
        monetary_analyzer = MonetaryFactorAnalyzer(fred_api_key=fred_api_key)
        try:
            monetary_result = monetary_analyzer.analyze(ticker)
        except Exception as e:
            monetary_result = {'success': False, 'error': str(e)}
        
        # Company Analysis
        company_analyzer = CompanyPerformanceAnalyzer()
        try:
            company_result = company_analyzer.analyze(ticker, verbose=False)
        except Exception as e:
            company_result = {'success': False, 'error': str(e)}
        
        # Supplier Analysis
        try:
            if anthropic_api_key:
                supplier_analyzer = SupplierAnalyzer(anthropic_api_key=anthropic_api_key)
                supplier_result = supplier_analyzer.analyze(ticker, verbose=False)
            else:
                supplier_result = {'success': False, 'error': 'Anthropic API key required'}
        except Exception as e:
            supplier_result = {'success': False, 'error': str(e)}
        
        # Customer Analysis
        try:
            if anthropic_api_key:
                customer_analyzer = CustomerAnalyzer(anthropic_api_key=anthropic_api_key)
                customer_result = customer_analyzer.analyze(ticker, verbose=False)
            else:
                customer_result = {'success': False, 'error': 'Anthropic API key required'}
        except Exception as e:
            customer_result = {'success': False, 'error': str(e)}
        
        # Macro Factors (NEW!)
        try:
            if anthropic_api_key:
                macro_analyzer = MacroFactorAnalyzer(anthropic_api_key=anthropic_api_key)
                macro_result = macro_analyzer.analyze(ticker, verbose=False)
            else:
                macro_result = {'success': False, 'error': 'Anthropic API key required'}
        except Exception as e:
            macro_result = {'success': False, 'error': str(e)}
    
    # TAB 1: Summary
    with tab1:
        st.markdown(f"## {ticker} - Complete Analysis")
        
        monetary_ok = monetary_result.get('success', False)
        company_ok = company_result.get('success', False)
        supplier_ok = supplier_result.get('success', False)
        customer_ok = customer_result.get('success', False)
        macro_ok = macro_result.get('success', False)
        
        if monetary_ok or company_ok or supplier_ok or customer_ok or macro_ok:
            scores = []
            weights = []
            
            if monetary_ok:
                scores.append(monetary_result['score'])
                weights.append(0.25)
            
            if company_ok:
                scores.append(company_result['score'])
                weights.append(0.25)
            
            if supplier_ok:
                scores.append(supplier_result['score'])
                weights.append(0.15)
            
            if customer_ok:
                scores.append(customer_result['score'])
                weights.append(0.15)
            
            if macro_ok:
                scores.append(macro_result['score'])
                weights.append(0.20)
            
            total_weight = sum(weights)
            normalized_weights = [w/total_weight for w in weights]
            combined_score = round(sum(s*w for s, w in zip(scores, normalized_weights)), 1)
            
            if combined_score >= 7.5:
                overall_signal = "STRONG BUY"
            elif combined_score >= 6.5:
                overall_signal = "BUY"
            elif combined_score >= 5.5:
                overall_signal = "HOLD"
            else:
                overall_signal = "SELL"
            
            st.markdown("### 🎯 Overall Assessment")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Combined Score", f"{combined_score}/10")
            with col2:
                st.metric("Overall Signal", overall_signal)
            with col3:
                modules_active = sum([monetary_ok, company_ok, supplier_ok, customer_ok, macro_ok])
                st.metric("Modules Active", f"{modules_active}/5")
            
            # Module breakdown
            st.markdown("---")
            st.markdown("### 📊 Module Breakdown")
            
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                if monetary_ok:
                    score = monetary_result['score']
                    color = "🟢" if score >= 7 else "🟡" if score >= 6 else "🔴"
                    st.markdown(f"#### {color} Monetary")
                    st.metric("Score", f"{score}/10")
                    st.caption(f"Weight: 25%")
            
            with col2:
                if company_ok:
                    score = company_result['score']
                    color = "🟢" if score >= 7 else "🟡" if score >= 6 else "🔴"
                    st.markdown(f"#### {color} Company")
                    st.metric("Score", f"{score}/10")
                    st.caption(f"Weight: 25%")
            
            with col3:
                if supplier_ok:
                    score = supplier_result['score']
                    color = "🟢" if score >= 7 else "🟡" if score >= 5.5 else "🔴"
                    st.markdown(f"#### {color} Supply")
                    st.metric("Score", f"{score}/10")
                    st.caption(f"Weight: 15%")
            
            with col4:
                if customer_ok:
                    score = customer_result['score']
                    color = "🟢" if score >= 7 else "🟡" if score >= 5.5 else "🔴"
                    st.markdown(f"#### {color} Demand")
                    st.metric("Score", f"{score}/10")
                    st.caption(f"Weight: 15%")
            
            with col5:
                if macro_ok:
                    score = macro_result['score']
                    color = "🟢" if score >= 7 else "🟡" if score >= 5.5 else "🔴"
                    st.markdown(f"#### {color} Macro")
                    st.metric("Score", f"{score}/10")
                    st.caption(f"Weight: 20%")
        else:
            st.error("All modules failed")
    
    # TAB 2-5: Existing tabs (Monetary, Company, Suppliers, Customers)
    # [Previous code for these tabs remains the same - truncated for brevity]
    
    # TAB 6: Macro Factors (NEW!)
    with tab6:
        st.markdown(f"## 🌍 Macro Factors: {ticker}")
        
        if not anthropic_api_key:
            st.warning("⚠️ Anthropic API key required")
        elif macro_result.get('success'):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Macro Score", f"{macro_result['score']}/10")
            with col2:
                st.metric("Assessment", macro_result['signal'])
            with col3:
                st.metric("API Cost", f"${macro_result.get('estimated_cost', 0):.3f}")
            
            st.markdown("---")
            st.markdown("### 📊 Factor Breakdown")
            
            # Geopolitical
            geo = macro_result.get('geopolitical', {})
            if geo.get('success'):
                with st.expander("🌍 Geopolitical Risk", expanded=True):
                    st.markdown(f"**Score:** {geo.get('overall_score', 0):+.1f}/2.0")
                    if geo.get('summary'):
                        st.info(geo['summary'])
                    if geo.get('key_risks'):
                        st.markdown("**Key Risks:**")
                        for risk in geo['key_risks']:
                            st.markdown(f"• {risk}")
            
            # Regulatory
            reg = macro_result.get('regulatory', {})
            if reg.get('success'):
                with st.expander("⚖️ Regulatory Risk"):
                    st.markdown(f"**Score:** {reg.get('overall_score', 0):+.1f}/2.0")
                    if reg.get('summary'):
                        st.info(reg['summary'])
                    if reg.get('key_risks'):
                        st.markdown("**Key Risks:**")
                        for risk in reg['key_risks']:
                            st.markdown(f"• {risk}")
            
            # Industry
            ind = macro_result.get('industry', {})
            if ind.get('success'):
                with st.expander("📈 Industry Dynamics"):
                    st.markdown(f"**Score:** {ind.get('overall_score', 0):+.1f}/2.0")
                    if ind.get('summary'):
                        st.info(ind['summary'])
                    if ind.get('key_trends'):
                        st.markdown("**Key Trends:**")
                        for trend in ind['key_trends']:
                            st.markdown(f"• {trend}")
            
            # Commodity
            com = macro_result.get('commodity', {})
            if com.get('success'):
                with st.expander("🛢️ Commodity & Input Risk"):
                    st.markdown(f"**Score:** {com.get('overall_score', 0):+.1f}/2.0")
                    if com.get('summary'):
                        st.info(com['summary'])
                    if com.get('key_risks'):
                        st.markdown("**Key Risks:**")
                        for risk in com['key_risks']:
                            st.markdown(f"• {risk}")
            
            # ESG
            esg = macro_result.get('esg', {})
            if esg.get('success'):
                with st.expander("🌱 ESG Factors"):
                    st.markdown(f"**Score:** {esg.get('overall_score', 0):+.1f}/2.0")
                    if esg.get('summary'):
                        st.info(esg['summary'])
                    if esg.get('key_issues'):
                        st.markdown("**Key Issues:**")
                        for issue in esg['key_issues']:
                            st.markdown(f"• {issue}")
        else:
            st.error(f"❌ Error: {macro_result.get('error')}")

# Disclaimer
st.markdown("---")
st.markdown("""
<div style="background-color: #fff3cd; padding: 1rem; border-radius: 0.5rem;">
    <strong>⚠️ DISCLAIMER</strong><br>
    For educational purposes only. NOT investment advice.
</div>
""", unsafe_allow_html=True)
