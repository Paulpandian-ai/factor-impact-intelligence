"""
Factor Impact Intelligence - Enhanced with Web Search Supplier Analysis
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

st.set_page_config(page_title="Factor Impact Intelligence", page_icon="💰", layout="wide")

# Header
st.markdown("# 💰 Factor Impact Intelligence")
st.markdown("### AI-Powered Multi-Factor Stock Analysis")

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
    ### 🚀 Enhanced Features
    - ✅ Web search for supplier identification
    - ✅ Deep 10-K analysis
    - ✅ Quantitative + Qualitative impact
    - ✅ Opportunities, Challenges, Risks
    
    ### Modules Active
    - ✅ Module 0: Monetary Factors
    - ✅ Module 1: Company Performance
    - ✅ Module 2: Enhanced Supplier Analysis
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
        else:
            signal = "SELL"
        
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
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Summary", "💰 Monetary", "📄 Company", "🏭 Suppliers"])
    
    with st.spinner(f"Analyzing {ticker} across all modules..."):
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
        
        # Supplier Analysis (Enhanced with web search)
        try:
            if anthropic_api_key:
                supplier_analyzer = SupplierAnalyzer(anthropic_api_key=anthropic_api_key)
                supplier_result = supplier_analyzer.analyze(ticker, verbose=False)
            else:
                supplier_result = {'success': False, 'error': 'Anthropic API key required'}
        except Exception as e:
            supplier_result = {'success': False, 'error': str(e)}
    
    # TAB 1: Summary
    with tab1:
        st.markdown(f"## {ticker} - Multi-Module Analysis")
        
        monetary_ok = monetary_result.get('success', False)
        company_ok = company_result.get('success', False)
        supplier_ok = supplier_result.get('success', False)
        
        if monetary_ok or company_ok or supplier_ok:
            scores = []
            weights = []
            
            if monetary_ok:
                scores.append(monetary_result['score'])
                weights.append(0.4)
            
            if company_ok:
                scores.append(company_result['score'])
                weights.append(0.35)
            
            if supplier_ok:
                scores.append(supplier_result['score'])
                weights.append(0.25)
            
            total_weight = sum(weights)
            normalized_weights = [w/total_weight for w in weights]
            combined_score = round(sum(s*w for s, w in zip(scores, normalized_weights)), 1)
            
            if combined_score >= 7.5:
                overall_signal = "STRONG BUY"
            elif combined_score >= 6.5:
                overall_signal = "BUY"
            elif combined_score >= 5.5:
                overall_signal = "HOLD (Lean Buy)"
            else:
                overall_signal = "HOLD/SELL"
            
            st.markdown("### 🎯 Overall Assessment")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Combined Score", f"{combined_score}/10")
            with col2:
                st.metric("Overall Signal", overall_signal)
            with col3:
                modules_active = sum([monetary_ok, company_ok, supplier_ok])
                st.metric("Modules Active", f"{modules_active}/3")
            
            # Module breakdown
            st.markdown("---")
            st.markdown("### 📊 Module Breakdown")
            
            if supplier_ok:
                col1, col2, col3 = st.columns(3)
            else:
                col1, col2 = st.columns(2)
            
            with col1:
                if monetary_ok:
                    score = monetary_result['score']
                    color = "🟢" if score >= 7.5 else "🟡" if score >= 6.5 else "🔴"
                    st.markdown(f"#### {color} Monetary")
                    st.metric("Score", f"{score}/10")
                    st.caption(monetary_result['signal'])
            
            with col2:
                if company_ok:
                    score = company_result['score']
                    color = "🟢" if score >= 7.5 else "🟡" if score >= 6.5 else "🔴"
                    st.markdown(f"#### {color} Company")
                    st.metric("Score", f"{score}/10")
                    st.caption(company_result['signal'])
            
            if supplier_ok:
                with col3:
                    score = supplier_result['score']
                    color = "🟢" if score >= 7.0 else "🟡" if score >= 5.5 else "🔴"
                    st.markdown(f"#### {color} Suppliers")
                    st.metric("Risk Score", f"{score}/10")
                    st.caption(supplier_result['signal'])
        else:
            st.error("All modules failed")
    
    # TAB 2: Monetary
    with tab2:
        st.markdown(f"## 💰 Monetary Factor Analysis: {ticker}")
        
        if monetary_result.get('success'):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Score", f"{monetary_result['score']}/10")
            with col2:
                st.metric("Signal", monetary_result['signal'])
            with col3:
                if monetary_result.get('beta'):
                    st.metric("Beta", f"{monetary_result['beta']:.2f}")
            
            st.markdown("### Factor Scores")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("#### 🏦 Fed Rate")
                st.metric("Score", f"{monetary_result['fed_score']:+.1f}/2.0")
                if monetary_result.get('fed'):
                    st.info(f"Current: {monetary_result['fed']['current']:.2f}%")
            
            with col2:
                st.markdown("#### 📊 Inflation")
                st.metric("Score", f"{monetary_result['inf_score']:+.1f}/2.0")
                if monetary_result.get('inf'):
                    st.info(f"YoY: {monetary_result['inf']['yoy']:.2f}%")
            
            with col3:
                st.markdown("#### 📈 Yields")
                st.metric("Score", f"{monetary_result['yld_score']:+.1f}/2.0")
                if monetary_result.get('yld'):
                    st.info(f"10Y: {monetary_result['yld']['current']:.2f}%")
        else:
            st.error(f"Error: {monetary_result.get('error')}")
    
    # TAB 3: Company
    with tab3:
        st.markdown(f"## 📄 Company Performance: {ticker}")
        
        if company_result.get('success'):
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Score", f"{company_result['score']}/10")
            with col2:
                st.metric("Signal", company_result['signal'])
            
            if company_result.get('data_date'):
                st.caption(f"📅 Data: {company_result['data_date']}")
            
            factors = company_result.get('factors', {})
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("#### 📊 Revenue")
                rev = factors.get('revenue_growth', {})
                st.metric("Score", f"{rev.get('score', 0):+.1f}/2.0")
                st.caption(rev.get('reasoning', 'N/A'))
            
            with col2:
                st.markdown("#### 📈 Margins")
                margin = factors.get('margins', {})
                st.metric("Score", f"{margin.get('score', 0):+.1f}/2.0")
                st.caption(margin.get('reasoning', 'N/A'))
            
            with col3:
                st.markdown("#### 🏥 Health")
                health = factors.get('financial_health', {})
                st.metric("Score", f"{health.get('score', 0):+.1f}/2.0")
                st.caption(health.get('reasoning', 'N/A'))
        else:
            st.error(f"Error: {company_result.get('error')}")
    
    # TAB 4: Enhanced Supplier Analysis
    with tab4:
        st.markdown(f"## 🏭 Enhanced Supplier Analysis: {ticker}")
        
        if not anthropic_api_key:
            st.warning("⚠️ Anthropic API key required")
            st.info("Add your API key in the sidebar")
        elif supplier_result.get('success'):
            # Header metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Risk Score", f"{supplier_result['score']}/10")
            with col2:
                st.metric("Risk Level", supplier_result['signal'])
            with col3:
                st.metric("Suppliers", len(supplier_result.get('suppliers', [])))
            with col4:
                st.metric("API Cost", f"${supplier_result.get('estimated_cost', 0):.3f}")
            
            st.caption(f"🔍 Search Quality: {supplier_result.get('search_quality', 'Unknown')}")
            st.caption(f"💰 Tokens Used: {supplier_result.get('tokens_used', 0):,}")
            
            # Overall assessment
            st.markdown("---")
            st.markdown("### 🎯 Overall Assessment")
            st.info(f"**Overall Risk:** {supplier_result.get('overall_supplier_risk', 'Unknown')}")
            
            if supplier_result.get('key_findings'):
                st.markdown("**Key Findings:**")
                for finding in supplier_result['key_findings']:
                    st.markdown(f"• {finding}")
            
            # Detailed supplier analysis
            st.markdown("---")
            st.markdown("### 📋 Detailed Supplier Analysis")
            
            suppliers = supplier_result.get('suppliers', [])
            
            for i, supplier in enumerate(suppliers):
                with st.expander(
                    f"**{i+1}. {supplier['name']}** ({supplier.get('ticker', 'PRIVATE')}) - Score: {supplier.get('score', 0):+.1f}/2.0",
                    expanded=(i==0)
                ):
                    # Basic Info
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.markdown(f"**Supplies:** {supplier.get('supplies', 'N/A')}")
                        st.markdown(f"**Importance:** {supplier.get('importance', 'N/A')}")
                        st.markdown(f"**Financial Exposure:** {supplier.get('financial_exposure', 'Not disclosed')}")
                        if supplier.get('recent_context'):
                            st.markdown(f"**Recent:** {supplier['recent_context']}")
                    
                    with col2:
                        if supplier.get('ticker') != 'PRIVATE':
                            st.metric("Ticker", supplier['ticker'])
                        else:
                            st.caption("🔒 Private Company")
                    
                    # Financial Metrics
                    if supplier.get('financials'):
                        st.markdown("---")
                        st.markdown("**📊 Financial Metrics**")
                        
                        fin = supplier['financials']
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            if fin.get('market_cap'):
                                st.metric("Market Cap", f"${fin['market_cap']/1e9:.1f}B")
                        with col2:
                            if fin.get('revenue'):
                                st.metric("Revenue (Q)", f"${fin['revenue']/1e9:.1f}B")
                        with col3:
                            if fin.get('profit_margin'):
                                st.metric("Margin", f"{fin['profit_margin']*100:.1f}%")
                        with col4:
                            if fin.get('revenue_growth'):
                                st.metric("Growth", f"{fin['revenue_growth']:+.1f}%")
                    
                    # Impact Analysis
                    if supplier.get('impact_analysis') and supplier['impact_analysis'].get('success'):
                        impact = supplier['impact_analysis']
                        
                        st.markdown("---")
                        st.markdown("**🎯 Impact Analysis**")
                        
                        # Quantitative
                        if impact.get('quantitative'):
                            st.markdown("**📊 Quantitative Impact:**")
                            quant = impact['quantitative']
                            st.markdown(f"• **Financial Scale:** {quant.get('financial_scale', 'N/A')}")
                            st.markdown(f"• **Capacity:** {quant.get('capacity_assessment', 'N/A')}")
                            st.markdown(f"• **Investment:** {quant.get('investment_outlook', 'N/A')}")
                            st.markdown(f"• **Dependency:** {quant.get('mutual_dependency', 'N/A')}")
                        
                        # Qualitative
                        if impact.get('qualitative'):
                            st.markdown("**💭 Qualitative Impact:**")
                            qual = impact['qualitative']
                            st.markdown(f"• **Strategic Importance:** {qual.get('strategic_importance', 'N/A')}")
                            st.markdown(f"• **Relationship:** {qual.get('relationship_strength', 'N/A')}")
                            st.markdown(f"• **Risk Level:** {qual.get('risk_level', 'N/A')}")
                            st.markdown(f"• **Alternatives:** {qual.get('alternative_availability', 'N/A')}")
                        
                        # Opportunities, Challenges, Risks
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            if impact.get('opportunities'):
                                st.success("**✅ Opportunities**")
                                for opp in impact['opportunities']:
                                    st.markdown(f"• {opp}")
                        
                        with col2:
                            if impact.get('challenges'):
                                st.warning("**⚠️ Challenges**")
                                for ch in impact['challenges']:
                                    st.markdown(f"• {ch}")
                        
                        with col3:
                            if impact.get('risks'):
                                st.error("**🚨 Risks**")
                                for risk in impact['risks']:
                                    st.markdown(f"• {risk}")
                        
                        # Summary and Reliability
                        if impact.get('summary'):
                            st.info(f"**Summary:** {impact['summary']}")
                        
                        if impact.get('reliability_score'):
                            st.metric("Reliability Score", f"{impact['reliability_score']}/10")
        else:
            st.error(f"❌ Error: {supplier_result.get('error', 'Unknown error')}")

# Disclaimer
st.markdown("---")
st.markdown("""
<div style="background-color: #fff3cd; padding: 1rem; border-radius: 0.5rem;">
    <strong>⚠️ DISCLAIMER</strong><br>
    For educational purposes only. NOT investment advice.
</div>
""", unsafe_allow_html=True)
