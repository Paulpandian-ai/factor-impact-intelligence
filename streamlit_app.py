"""
Factor Impact Intelligence - Complete Platform
WITH ANALYST CRITIQUE MODULE (Module 8) - FIXED VERSION
Handles file upload without losing analysis state
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
from analyst_critique import AnalystCritique

st.set_page_config(page_title="Factor Impact Intelligence", page_icon="💰", layout="wide")

# Initialize session state
if 'analysis_complete' not in st.session_state:
    st.session_state.analysis_complete = False
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = {}

# Header
st.markdown("# 💰 Factor Impact Intelligence")
st.markdown("### Complete Multi-Factor Stock Analysis Platform")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    
    if 'fred_api_key' in st.secrets:
        fred_api_key = st.secrets['fred_api_key']
        st.success("✅ FRED API loaded")
    else:
        fred_api_key = st.text_input("FRED API Key", type="password")
    
    st.markdown("---")
    
    if 'ANTHROPIC_API_KEY' in st.secrets:
        anthropic_api_key = st.secrets['ANTHROPIC_API_KEY']
        st.success("✅ Anthropic API loaded")
    else:
        anthropic_api_key = st.text_input("Anthropic API Key", type="password")
    
    st.markdown("---")
    st.markdown("""
    ### 📊 Active Modules (6)
    - ✅ Module 0: Monetary
    - ✅ Module 1: Company
    - ✅ Module 2: Suppliers
    - ✅ Module 3: Customers
    - ✅ Module 5: Macro
    - ✅ Module 8: Analyst Critique 🆕
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

# Run analysis if button clicked
if analyze_btn and ticker:
    with st.spinner(f"Analyzing {ticker} (90-120 seconds)..."):
        # Run all analyses
        monetary_analyzer = MonetaryFactorAnalyzer(fred_api_key=fred_api_key)
        try:
            monetary_result = monetary_analyzer.analyze(ticker)
        except Exception as e:
            monetary_result = {'success': False, 'error': str(e)}
        
        company_analyzer = CompanyPerformanceAnalyzer()
        try:
            company_result = company_analyzer.analyze(ticker, verbose=False)
        except Exception as e:
            company_result = {'success': False, 'error': str(e)}
        
        try:
            if anthropic_api_key:
                supplier_analyzer = SupplierAnalyzer(anthropic_api_key=anthropic_api_key)
                supplier_result = supplier_analyzer.analyze(ticker, verbose=False)
            else:
                supplier_result = {'success': False, 'error': 'API key required'}
        except Exception as e:
            supplier_result = {'success': False, 'error': str(e)}
        
        try:
            if anthropic_api_key:
                customer_analyzer = CustomerAnalyzer(anthropic_api_key=anthropic_api_key)
                customer_result = customer_analyzer.analyze(ticker, verbose=False)
            else:
                customer_result = {'success': False, 'error': 'API key required'}
        except Exception as e:
            customer_result = {'success': False, 'error': str(e)}
        
        try:
            if anthropic_api_key:
                macro_analyzer = MacroFactorAnalyzer(anthropic_api_key=anthropic_api_key)
                macro_result = macro_analyzer.analyze(ticker, verbose=False)
            else:
                macro_result = {'success': False, 'error': 'API key required'}
        except Exception as e:
            macro_result = {'success': False, 'error': str(e)}
    
    # Store results in session state
    st.session_state.analysis_results = {
        'ticker': ticker,
        'monetary': monetary_result,
        'company': company_result,
        'suppliers': supplier_result,
        'customers': customer_result,
        'macro': macro_result
    }
    st.session_state.analysis_complete = True

# Show tabs if analysis is complete
if st.session_state.analysis_complete:
    # Get results from session state
    results = st.session_state.analysis_results
    ticker = results['ticker']
    monetary_result = results['monetary']
    company_result = results['company']
    supplier_result = results['suppliers']
    customer_result = results['customers']
    macro_result = results['macro']
    
    # Create tabs
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📊 Summary", "💰 Monetary", "📄 Company", 
        "🏭 Suppliers", "👥 Customers", "🌍 Macro", "🎯 Analyst Critique"
    ])
    
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
            
            # Store combined score
            st.session_state.analysis_results['combined_score'] = combined_score
            st.session_state.analysis_results['combined_signal'] = overall_signal
            
            st.markdown("### 🎯 Overall Assessment")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Combined Score", f"{combined_score}/10")
            with col2:
                st.metric("Overall Signal", overall_signal)
            with col3:
                modules_active = sum([monetary_ok, company_ok, supplier_ok, customer_ok, macro_ok])
                st.metric("Modules Active", f"{modules_active}/5")
            
            st.markdown("---")
            st.markdown("### 📊 Module Breakdown")
            
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                if monetary_ok:
                    score = monetary_result['score']
                    color = "🟢" if score >= 7 else "🟡" if score >= 6 else "🔴"
                    st.markdown(f"#### {color} Monetary")
                    st.metric("Score", f"{score}/10")
                    st.caption("Weight: 25%")
            
            with col2:
                if company_ok:
                    score = company_result['score']
                    color = "🟢" if score >= 7 else "🟡" if score >= 6 else "🔴"
                    st.markdown(f"#### {color} Company")
                    st.metric("Score", f"{score}/10")
                    st.caption("Weight: 25%")
            
            with col3:
                if supplier_ok:
                    score = supplier_result['score']
                    color = "🟢" if score >= 7 else "🟡" if score >= 5.5 else "🔴"
                    st.markdown(f"#### {color} Supply")
                    st.metric("Score", f"{score}/10")
                    st.caption("Weight: 15%")
            
            with col4:
                if customer_ok:
                    score = customer_result['score']
                    color = "🟢" if score >= 7 else "🟡" if score >= 5.5 else "🔴"
                    st.markdown(f"#### {color} Demand")
                    st.metric("Score", f"{score}/10")
                    st.caption("Weight: 15%")
            
            with col5:
                if macro_ok:
                    score = macro_result['score']
                    color = "🟢" if score >= 7 else "🟡" if score >= 5.5 else "🔴"
                    st.markdown(f"#### {color} Macro")
                    st.metric("Score", f"{score}/10")
                    st.caption("Weight: 20%")
        else:
            st.error("All modules failed")
    
    # TAB 2: Monetary
    with tab2:
        st.markdown(f"## 💰 Monetary Analysis: {ticker}")
        
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
    
    # TAB 4: Suppliers
    with tab4:
        st.markdown(f"## 🏭 Supplier Analysis: {ticker}")
        
        if not anthropic_api_key:
            st.warning("⚠️ Anthropic API key required")
        elif supplier_result.get('success'):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Risk Score", f"{supplier_result['score']}/10")
            with col2:
                st.metric("Risk Level", supplier_result['signal'])
            with col3:
                st.metric("Suppliers", len(supplier_result.get('suppliers', [])))
            
            if supplier_result.get('key_findings'):
                st.markdown("**Key Findings:**")
                for finding in supplier_result['key_findings']:
                    st.markdown(f"• {finding}")
            
            st.markdown("---")
            for i, supplier in enumerate(supplier_result.get('suppliers', [])):
                with st.expander(f"**{i+1}. {supplier['name']}** - {supplier.get('score', 0):+.1f}/2.0"):
                    st.markdown(f"**Supplies:** {supplier.get('supplies', 'N/A')}")
                    st.markdown(f"**Importance:** {supplier.get('importance', 'N/A')}")
                    
                    if supplier.get('impact_analysis') and supplier['impact_analysis'].get('success'):
                        impact = supplier['impact_analysis']
                        if impact.get('summary'):
                            st.info(impact['summary'])
        else:
            st.error(f"Error: {supplier_result.get('error')}")
    
    # TAB 5: Customers
    with tab5:
        st.markdown(f"## 👥 Customer Analysis: {ticker}")
        
        if not anthropic_api_key:
            st.warning("⚠️ Anthropic API key required")
        elif customer_result.get('success'):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Demand Score", f"{customer_result['score']}/10")
            with col2:
                st.metric("Outlook", customer_result['signal'])
            with col3:
                st.metric("Customers", len(customer_result.get('customers', [])))
            
            if customer_result.get('key_findings'):
                st.markdown("**Key Findings:**")
                for finding in customer_result['key_findings']:
                    st.markdown(f"• {finding}")
            
            st.markdown("---")
            for i, customer in enumerate(customer_result.get('customers', [])):
                with st.expander(f"**{i+1}. {customer['name']}** - {customer.get('score', 0):+.1f}/2.0"):
                    st.markdown(f"**Purchases:** {customer.get('purchases', 'N/A')}")
                    st.markdown(f"**Importance:** {customer.get('importance', 'N/A')}")
                    
                    if customer.get('demand_analysis') and customer['demand_analysis'].get('success'):
                        demand = customer['demand_analysis']
                        if demand.get('summary'):
                            st.info(demand['summary'])
        else:
            st.error(f"Error: {customer_result.get('error')}")
    
    # TAB 6: Macro Factors
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
                cost = macro_result.get('estimated_cost', 0)
                st.metric("API Cost", f"${cost:.3f}")
            
            st.markdown("---")
            st.markdown("### 📊 Factor Breakdown")
            st.caption("Weights: 🌍 Geopolitical 30% | ⚖️ Regulatory 25% | 📈 Industry 25% | 🛢️ Commodity 15% | 🌱 ESG 5%")
            st.markdown("")
            
            geo = macro_result.get('geopolitical') or {}
            reg = macro_result.get('regulatory') or {}
            ind = macro_result.get('industry') or {}
            com = macro_result.get('commodity') or {}
            esg = macro_result.get('esg') or {}
            
            with st.expander("🌍 **Geopolitical Risk** (30% weight)", expanded=True):
                if geo and (geo.get('success') or geo.get('overall_score') is not None):
                    score = geo.get('overall_score', 0)
                    if score >= 0:
                        st.success(f"**Score: {score:+.1f}/2.0** (Low Risk)")
                    elif score >= -1:
                        st.warning(f"**Score: {score:+.1f}/2.0** (Moderate Risk)")
                    else:
                        st.error(f"**Score: {score:+.1f}/2.0** (High Risk)")
                    if geo.get('summary'):
                        st.markdown("**Summary:**")
                        st.info(geo['summary'])
                    if geo.get('key_risks'):
                        st.markdown("**Key Risks:**")
                        for risk in geo['key_risks']:
                            st.markdown(f"• {risk}")
                else:
                    st.error("Geopolitical analysis not available")
            
            with st.expander("⚖️ **Regulatory Risk** (25% weight)"):
                if reg and (reg.get('success') or reg.get('overall_score') is not None):
                    score = reg.get('overall_score', 0)
                    if score >= 0:
                        st.success(f"**Score: {score:+.1f}/2.0** (Low Risk)")
                    elif score >= -1:
                        st.warning(f"**Score: {score:+.1f}/2.0** (Moderate Risk)")
                    else:
                        st.error(f"**Score: {score:+.1f}/2.0** (High Risk)")
                    if reg.get('summary'):
                        st.markdown("**Summary:**")
                        st.info(reg['summary'])
                    if reg.get('key_risks'):
                        st.markdown("**Key Risks:**")
                        for risk in reg['key_risks']:
                            st.markdown(f"• {risk}")
                else:
                    st.error("Regulatory analysis not available")
            
            with st.expander("📈 **Industry Dynamics** (25% weight)"):
                if ind and (ind.get('success') or ind.get('overall_score') is not None):
                    score = ind.get('overall_score', 0)
                    if score >= 1:
                        st.success(f"**Score: {score:+.1f}/2.0** (Strong)")
                    elif score >= 0:
                        st.info(f"**Score: {score:+.1f}/2.0** (Neutral)")
                    else:
                        st.warning(f"**Score: {score:+.1f}/2.0** (Weak)")
                    if ind.get('summary'):
                        st.markdown("**Summary:**")
                        st.info(ind['summary'])
                    if ind.get('key_trends'):
                        st.markdown("**Key Trends:**")
                        for trend in ind['key_trends']:
                            st.markdown(f"• {trend}")
                else:
                    st.error("Industry analysis not available")
            
            with st.expander("🛢️ **Commodity & Input Risk** (15% weight)"):
                if com and (com.get('success') or com.get('overall_score') is not None):
                    score = com.get('overall_score', 0)
                    if score >= 0:
                        st.success(f"**Score: {score:+.1f}/2.0** (Low Risk)")
                    elif score >= -1:
                        st.warning(f"**Score: {score:+.1f}/2.0** (Moderate Risk)")
                    else:
                        st.error(f"**Score: {score:+.1f}/2.0** (High Risk)")
                    if com.get('summary'):
                        st.markdown("**Summary:**")
                        st.info(com['summary'])
                    if com.get('key_risks'):
                        st.markdown("**Key Risks:**")
                        for risk in com['key_risks']:
                            st.markdown(f"• {risk}")
                else:
                    st.error("Commodity analysis not available")
            
            with st.expander("🌱 **ESG Factors** (5% weight)"):
                if esg and (esg.get('success') or esg.get('overall_score') is not None):
                    score = esg.get('overall_score', 0)
                    if score >= 0:
                        st.success(f"**Score: {score:+.1f}/2.0** (Low Risk)")
                    elif score >= -1:
                        st.warning(f"**Score: {score:+.1f}/2.0** (Moderate Risk)")
                    else:
                        st.error(f"**Score: {score:+.1f}/2.0** (High Risk)")
                    if esg.get('summary'):
                        st.markdown("**Summary:**")
                        st.info(esg['summary'])
                    if esg.get('key_issues'):
                        st.markdown("**Key Issues:**")
                        for issue in esg['key_issues']:
                            st.markdown(f"• {issue}")
                else:
                    st.error("ESG analysis not available")
            
            st.markdown("---")
            st.markdown("### 💡 Overall Macro Assessment")
            
            st.markdown(f"""
**Weighted Calculation:**
- 🌍 Geopolitical: {geo.get('overall_score', 0):+.1f} × 30% = {geo.get('overall_score', 0) * 0.30:+.2f}
- ⚖️ Regulatory: {reg.get('overall_score', 0):+.1f} × 25% = {reg.get('overall_score', 0) * 0.25:+.2f}
- 📈 Industry: {ind.get('overall_score', 0):+.1f} × 25% = {ind.get('overall_score', 0) * 0.25:+.2f}
- 🛢️ Commodity: {com.get('overall_score', 0):+.1f} × 15% = {com.get('overall_score', 0) * 0.15:+.2f}
- 🌱 ESG: {esg.get('overall_score', 0):+.1f} × 5% = {esg.get('overall_score', 0) * 0.05:+.2f}

**Final Score:** {macro_result['score']}/10 → {macro_result['signal']}
""")
            
        else:
            st.error(f"❌ Error: {macro_result.get('error', 'Unknown error')}")
    
    # TAB 7: ANALYST CRITIQUE
    with tab7:
        st.markdown(f"## 🎯 Analyst Critique: {ticker}")
        st.markdown("Upload an analyst report (PDF) to compare with our comprehensive analysis")
        
        if not anthropic_api_key:
            st.warning("⚠️ Anthropic API key required for analyst critique")
        else:
            uploaded_file = st.file_uploader(
                "Upload Analyst Report (PDF)",
                type=['pdf'],
                help="Upload Morningstar, Goldman Sachs, or any analyst report",
                key="analyst_pdf"
            )
            
            if uploaded_file is not None:
                st.success(f"✅ Uploaded: {uploaded_file.name}")
                
                if st.button("🔍 Critique This Report", type="primary", key="critique_btn"):
                    with st.spinner("Analyzing analyst report and generating critique..."):
                        try:
                            pdf_data = uploaded_file.read()
                            critique_engine = AnalystCritique(anthropic_api_key=anthropic_api_key)
                            platform_data = st.session_state.analysis_results
                            
                            result = critique_engine.generate_critique(
                                pdf_data=pdf_data,
                                filename=uploaded_file.name,
                                platform_data=platform_data
                            )
                            
                            if result.get('success'):
                                analyst_thesis = result['analyst_thesis']
                                critique = result['critique']
                                
                                st.markdown("---")
                                st.markdown("### 📄 Analyst's View")
                                
                                col1, col2, col3, col4 = st.columns(4)
                                with col1:
                                    st.metric("Firm", analyst_thesis.get('analyst_firm', 'Unknown'))
                                with col2:
                                    st.metric("Rating", analyst_thesis.get('rating', 'N/A'))
                                with col3:
                                    fv = analyst_thesis.get('fair_value')
                                    st.metric("Fair Value", f"${fv}" if fv else "N/A")
                                with col4:
                                    st.metric("Moat", analyst_thesis.get('economic_moat', 'N/A'))
                                
                                if analyst_thesis.get('key_thesis'):
                                    st.markdown("**Key Investment Thesis:**")
                                    for thesis in analyst_thesis['key_thesis']:
                                        st.markdown(f"• {thesis}")
                                
                                st.markdown("---")
                                st.markdown("### ✅ What They Got Right")
                                
                                for agree in critique.get('agreement_areas', []):
                                    with st.expander(f"✅ {agree.get('topic', 'Agreement')}"):
                                        st.markdown(f"**Analyst's View:** {agree.get('analyst_view', 'N/A')}")
                                        st.markdown(f"**Our Data:** {agree.get('our_data', 'N/A')}")
                                        st.success(agree.get('verdict', 'AGREE'))
                                
                                st.markdown("---")
                                st.markdown("### ⚠️ What They Missed")
                                
                                for missed in critique.get('missed_factors', []):
                                    severity = missed.get('severity', 'Medium')
                                    icon = "🔴" if severity == "High" else "🟡" if severity == "Medium" else "🟢"
                                    
                                    with st.expander(f"{icon} {missed.get('factor', 'Missed Factor')}"):
                                        st.markdown(f"**Why Important:** {missed.get('why_important', 'N/A')}")
                                        st.markdown(f"**Impact:** {missed.get('impact', 'N/A')}")
                                        st.warning(f"Severity: {severity}")
                                
                                if critique.get('underweighted_risks'):
                                    st.markdown("---")
                                    st.markdown("### 🔽 Underweighted Risks")
                                    
                                    for risk in critique['underweighted_risks']:
                                        with st.expander(f"⚠️ {risk.get('risk', 'Risk')}"):
                                            st.markdown(f"**Analyst Treatment:** {risk.get('analyst_treatment', 'N/A')}")
                                            st.markdown(f"**Our Assessment:** {risk.get('our_assessment', 'N/A')}")
                                            st.error(f"**Gap:** {risk.get('gap', 'N/A')}")
                                
                                st.markdown("---")
                                st.markdown("### 🎯 Our Adjusted View")
                                
                                adjusted = critique.get('our_adjusted_view', {})
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.metric("Our Price Target", adjusted.get('price_target', 'N/A'))
                                with col2:
                                    st.metric("Our Rating", adjusted.get('rating', 'N/A'))
                                
                                if adjusted.get('key_differences'):
                                    st.markdown("**Key Differences:**")
                                    for diff in adjusted['key_differences']:
                                        st.markdown(f"• {diff}")
                                
                                if adjusted.get('reasoning'):
                                    st.info(adjusted['reasoning'])
                                
                                st.markdown("---")
                                st.markdown("### 📝 Critique Summary")
                                st.markdown(critique.get('critique_summary', 'No summary available'))
                                
                                st.markdown("---")
                                st.caption(f"💰 Analysis Cost: ${result.get('estimated_cost', 0):.3f}")
                                
                            else:
                                st.error(f"❌ Error: {result.get('error', 'Unknown error')}")
                        
                        except Exception as e:
                            st.error(f"❌ Error processing report: {str(e)}")
            
            else:
                st.info("👆 Upload an analyst report to begin critique")
                
                with st.expander("📊 See Example Output"):
                    st.markdown("""
**Example: Morningstar NVDA Report Critique**

✅ **What They Got Right:**
- Strong AI demand fundamentals
- Wide economic moat
- High profitability metrics

⚠️ **What They Missed:**
- 🔴 Supply chain concentration (90% TSMC)
- 🔴 Geopolitical risk underweighted
- 🟡 Customer concentration not analyzed

🎯 **Adjusted View:**
- Analyst Fair Value: $240
- Our Target: $165-170
- Reason: Underweights geopolitical (-$10) and supply chain risk (-$10)
""")

# Disclaimer
st.markdown("---")
st.markdown("""
<div style="background-color: #fff3cd; padding: 1rem; border-radius: 0.5rem;">
    <strong>⚠️ DISCLAIMER</strong><br>
    For educational purposes only. NOT investment advice.
</div>
""", unsafe_allow_html=True)
