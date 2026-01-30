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
from supplier_analyzer import SupplierAnalyzer

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

    # After the FRED API key section
    st.markdown("---")

    if 'ANTHROPIC_API_KEY' in st.secrets:
        anthropic_api_key = st.secrets['ANTHROPIC_API_KEY']
        st.success("✅ Anthropic API loaded")
    else:
        anthropic_api_key = st.text_input("Anthropic API Key", type="password",
                                       help="Get key at console.anthropic.com")
    
    st.markdown("---")
    st.markdown("""
    ### Modules Active
    - ✅ Module 0: Monetary Factors
    - ✅ Module 1: Company Performance
    - ✅ Module 2: Supplier Analysis  ← NEW!
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
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Summary", "💰 Monetary", "📄 Company", "🏭 Suppliers"])
    
    with st.spinner(f"Analyzing {ticker} across all modules..."):
        # Run both analyses
        monetary_analyzer = MonetaryFactorAnalyzer(fred_api_key=fred_api_key)
        company_analyzer = CompanyPerformanceAnalyzer()
        
        try:
            monetary_result = monetary_analyzer.analyze(ticker)
        except Exception as e:
            monetary_result = {'success': False, 'error': str(e)}
        
        try:
            company_result = company_analyzer.analyze(ticker, verbose=False)
        except Exception as e:
            company_result = {'success': False, 'error': str(e)}
# After company_result
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
    
    # Check which modules succeeded
    monetary_ok = monetary_result.get('success', False)
    company_ok = company_result.get('success', False)
    supplier_ok = supplier_result.get('success', False)
    
    if monetary_ok or company_ok or supplier_ok:
        # Calculate combined score based on available modules
        scores = []
        weights = []
        
        if monetary_ok:
            scores.append(monetary_result['score'])
            weights.append(0.4)  # 40% weight
        
        if company_ok:
            scores.append(company_result['score'])
            weights.append(0.35)  # 35% weight
        
        if supplier_ok:
            # Supplier score is risk-based, so invert it
            # High supplier score = low risk = good
            # We already have it on 1-10 scale, so use directly
            scores.append(supplier_result['score'])
            weights.append(0.25)  # 25% weight
        
        # Normalize weights if not all modules available
        total_weight = sum(weights)
        normalized_weights = [w/total_weight for w in weights]
        
        # Calculate weighted average
        combined_score = round(sum(s*w for s, w in zip(scores, normalized_weights)), 1)
        
        # Overall signal
        if combined_score >= 7.5:
            overall_signal = "STRONG BUY"
        elif combined_score >= 6.5:
            overall_signal = "BUY"
        elif combined_score >= 5.5:
            overall_signal = "HOLD (Lean Buy)"
        elif combined_score >= 4.5:
            overall_signal = "HOLD"
        else:
            overall_signal = "SELL"
        
        # Display metrics
        st.markdown("### 🎯 Overall Assessment")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Combined Score", f"{combined_score}/10", help="Weighted average of all active modules")
        with col2:
            st.metric("Overall Signal", overall_signal)
        with col3:
            modules_active = sum([monetary_ok, company_ok, supplier_ok])
            st.metric("Modules Active", f"{modules_active}/3")
        
        # Gauge chart
        try:
            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=combined_score,
                title={'text': f"{ticker} Overall Score", 'font': {'size': 20}},
                gauge={
                    'axis': {'range': [0, 10]},
                    'bar': {'color': "darkblue"},
                    'steps': [
                        {'range': [0, 3], 'color': "#ffcccc"},
                        {'range': [3, 5], 'color': "#ffe6cc"},
                        {'range': [5, 7], 'color': "#ffffcc"},
                        {'range': [7, 8.5], 'color': "#ccffcc"},
                        {'range': [8.5, 10], 'color': "#99ff99"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': combined_score
                    }
                }
            ))
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.warning(f"Could not generate chart: {str(e)}")
        
        st.markdown("---")
        st.markdown("### 📊 Module Breakdown")
        
        # Create columns based on how many modules are active
        if supplier_ok:
            col1, col2, col3 = st.columns(3)
        else:
            col1, col2 = st.columns(2)
        
        # Monetary Module
        with col1:
            if monetary_ok:
                score = monetary_result['score']
                signal = monetary_result['signal']
                
                # Color based on score
                if score >= 7.5:
                    color = "🟢"
                elif score >= 6.5:
                    color = "🟡"
                else:
                    color = "🔴"
                
                st.markdown(f"#### {color} Monetary Factors")
                st.metric("Score", f"{score}/10")
                st.caption(f"**Signal:** {signal}")
                
                if monetary_result.get('beta'):
                    st.caption(f"Beta: {monetary_result['beta']:.2f}")
                
                if monetary_result.get('fed'):
                    st.caption(f"Fed: {monetary_result['fed']['current']:.2f}%")
                if monetary_result.get('inf'):
                    st.caption(f"CPI: {monetary_result['inf']['yoy']:.2f}%")
                
                st.caption("📅 Data: Oct 2025")
            else:
                st.markdown("#### ⚪ Monetary Factors")
                st.error("Analysis failed")
        
        # Company Module
        with col2:
            if company_ok:
                score = company_result['score']
                signal = company_result['signal']
                
                if score >= 7.5:
                    color = "🟢"
                elif score >= 6.5:
                    color = "🟡"
                else:
                    color = "🔴"
                
                st.markdown(f"#### {color} Company Performance")
                st.metric("Score", f"{score}/10")
                st.caption(f"**Signal:** {signal}")
                
                if company_result.get('data_date'):
                    st.caption(f"📅 Data: {company_result['data_date']}")
                    st.caption(f"🕐 {company_result['data_age_days']} days old")
            else:
                st.markdown("#### ⚪ Company Performance")
                st.error("Analysis failed")
        
        # Supplier Module (if available)
        if supplier_ok:
            with col3:
                score = supplier_result['score']
                signal = supplier_result['signal']
                
                # For supplier risk, LOWER score = HIGHER risk
                # So color logic is inverted
                if score >= 7.0:
                    color = "🟢"  # Low risk
                elif score >= 5.5:
                    color = "🟡"  # Moderate risk
                else:
                    color = "🔴"  # High risk
                
                st.markdown(f"#### {color} Supplier Analysis")
                st.metric("Risk Score", f"{score}/10")
                st.caption(f"**Risk Level:** {signal}")
                
                suppliers_count = len(supplier_result.get('suppliers', []))
                st.caption(f"Suppliers: {suppliers_count}")
                
                if supplier_result.get('filing_date'):
                    st.caption(f"📅 10-K: {supplier_result['filing_date']}")
                
                if supplier_result.get('estimated_cost'):
                    st.caption(f"💰 Cost: ${supplier_result['estimated_cost']:.3f}")
        
        # Key insights section
        st.markdown("---")
        st.markdown("### 💡 Key Insights")
        
        insights = []
        
        # Generate insights based on scores
        if monetary_ok and monetary_result['score'] >= 7.0:
            insights.append("✅ **Favorable monetary conditions** - Fed policy and inflation trends support growth")
        elif monetary_ok and monetary_result['score'] < 5.0:
            insights.append("⚠️ **Challenging monetary environment** - Rate pressures and inflation concerns")
        
        if company_ok and company_result['score'] >= 7.5:
            insights.append("✅ **Strong company fundamentals** - Excellent revenue growth and profitability")
        elif company_ok and company_result['score'] < 5.0:
            insights.append("⚠️ **Company performance concerns** - Weak financials or deteriorating metrics")
        
        if supplier_ok:
            if supplier_result['score'] >= 7.0:
                insights.append("✅ **Low supplier risk** - Diversified supplier base with healthy financials")
            elif supplier_result['score'] < 5.5:
                insights.append("⚠️ **Elevated supplier risk** - Concentration concerns or supplier financial stress")
            
            # Add key findings from supplier analysis
            if supplier_result.get('key_findings'):
                insights.append("**Supplier findings:**")
                for finding in supplier_result['key_findings'][:2]:  # Top 2
                    insights.append(f"  • {finding}")
        
        # Display insights
        if insights:
            for insight in insights:
                st.markdown(insight)
        else:
            st.info("Run all modules for comprehensive insights")
        
        # Module weights disclosure
        st.markdown("---")
        with st.expander("📋 How is the combined score calculated?"):
            st.markdown("""
            **Scoring Methodology:**
            
            The combined score is a weighted average of active modules:
            
            - **Monetary Factors:** 40% weight
              - Fed policy, inflation, Treasury yields
              - Measures macroeconomic tailwinds/headwinds
            
            - **Company Performance:** 35% weight
              - Revenue, profitability, margins, financial health, guidance
              - Measures fundamental business strength
            
            - **Supplier Analysis:** 25% weight
              - Supplier concentration, financial health, risks
              - Measures supply chain resilience (lower = higher risk)
            
            **Note:** Weights are automatically adjusted if modules are unavailable.
            
            **Example:**
            - Monetary: 7.1/10 × 40% = 2.84
            - Company: 9.6/10 × 35% = 3.36
            - Supplier: 6.5/10 × 25% = 1.63
            - **Combined: 7.83/10 → STRONG BUY**
            """)
    else:
        st.error("❌ All modules failed. Please check API keys and try again.")
        
        # Show specific errors
        if not monetary_ok:
            st.error(f"Monetary: {monetary_result.get('error', 'Unknown error')}")
        if not company_ok:
            st.error(f"Company: {company_result.get('error', 'Unknown error')}")
        if not supplier_ok:
            st.error(f"Supplier: {supplier_result.get('error', 'Unknown error')}")
    
    # TAB 2: Monetary Analysis
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
            
            # Data timestamp
            st.caption("📅 Data from: Oct 2025 (91 days old)")
            
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
            st.error(f"❌ Error: {monetary_result.get('error', 'Unable to fetch monetary data')}")
    
    # TAB 3: Company Analysis
    with tab3:
        st.markdown(f"## 📄 Company Performance Analysis: {ticker}")
        
        if company_result.get('success'):
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Company Score", f"{company_result['score']}/10")
            with col2:
                st.metric("Signal", company_result['signal'])
            
            # Data timestamp
            if company_result.get('data_date'):
                col1, col2 = st.columns(2)
                with col1:
                    st.caption(f"📅 Data from: {company_result['data_date']}")
                with col2:
                    st.caption(f"🕐 Age: {company_result['data_age_days']} days")
                
                if company_result.get('is_stale'):
                    st.warning("⚠️ Data is >6 months old - use caution")
            
            st.markdown("### Performance Factors")
            
            factors = company_result.get('factors', {})
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("#### 📊 Revenue Growth")
                rev_factor = factors.get('revenue_growth', {})
                st.metric("Score", f"{rev_factor.get('score', 0):+.1f}/2.0")
                st.caption(rev_factor.get('reasoning', 'N/A'))
                
                st.markdown("#### 💰 Profitability")
                prof_factor = factors.get('profitability', {})
                st.metric("Score", f"{prof_factor.get('score', 0):+.1f}/2.0")
                st.caption(prof_factor.get('reasoning', 'N/A'))
            
            with col2:
                st.markdown("#### 📈 Margins")
                margin_factor = factors.get('margins', {})
                st.metric("Score", f"{margin_factor.get('score', 0):+.1f}/2.0")
                st.caption(margin_factor.get('reasoning', 'N/A'))
                
                st.markdown("#### 🏥 Financial Health")
                health_factor = factors.get('financial_health', {})
                st.metric("Score", f"{health_factor.get('score', 0):+.1f}/2.0")
                st.caption(health_factor.get('reasoning', 'N/A'))
            
            with col3:
                st.markdown("#### 🎯 Guidance")
                guidance_factor = factors.get('guidance', {})
                st.metric("Score", f"{guidance_factor.get('score', 0):+.1f}/2.0")
                st.caption(guidance_factor.get('reasoning', 'N/A'))
        else:
            st.error(f"❌ Error: {company_result.get('error', 'Unable to fetch company data')}")

# TAB 4: Supplier Analysis
with tab4:
    st.markdown(f"## 🏭 Supplier Analysis: {ticker}")
    
    if not anthropic_api_key:
        st.warning("⚠️ Anthropic API key required for supplier analysis")
        st.info("Add your API key in the sidebar or Streamlit secrets")
        st.markdown("[Get API key at console.anthropic.com](https://console.anthropic.com/)")
    elif supplier_result.get('success'):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Supplier Risk Score", f"{supplier_result['score']}/10")
        with col2:
            st.metric("Risk Level", supplier_result['signal'])
        with col3:
            st.metric("Suppliers Analyzed", len(supplier_result.get('suppliers', [])))
        
        # Show filing date and cost
        st.caption(f"📅 Based on 10-K filed: {supplier_result.get('filing_date', 'N/A')}")
        st.caption(f"💰 API Cost: ${supplier_result.get('estimated_cost', 0):.3f} ({supplier_result.get('tokens_used', 0):,} tokens)")
        
        # Overall assessment
        st.markdown("### 🎯 Overall Assessment")
        st.info(f"**Overall Supplier Risk:** {supplier_result.get('overall_supplier_risk', 'Medium')}")
        
        # Key findings
        if supplier_result.get('key_findings'):
            st.markdown("**Key Findings:**")
            for finding in supplier_result['key_findings']:
                st.markdown(f"• {finding}")
        
        st.markdown("---")
        
        # Individual suppliers
        st.markdown("### 📋 Supplier Details")
        
        suppliers = supplier_result.get('suppliers', [])
        
        for i, supplier in enumerate(suppliers):
            with st.expander(f"**{i+1}. {supplier['name']}** - Score: {supplier['score']:+.1f}/2.0", expanded=(i==0)):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown(f"**Supplies:** {supplier.get('supplies', 'N/A')}")
                    st.markdown(f"**Importance:** {supplier.get('importance', 'N/A')}")
                    st.markdown(f"**Revenue Exposure:** {supplier.get('revenue_exposure', 'Not disclosed')}")
                    
                    if supplier.get('relationship_notes'):
                        st.markdown(f"**Relationship:** {supplier['relationship_notes']}")
                    
                    if supplier.get('quote'):
                        st.info(f"💬 \"{supplier['quote']}\"")
                
                with col2:
                    # Show ticker and financial status
                    ticker_display = supplier.get('ticker', 'PRIVATE')
                    if ticker_display != 'PRIVATE':
                        st.metric("Ticker", ticker_display)
                    else:
                        st.caption("🔒 Private Company")
                
                # Risks
                if supplier.get('risks'):
                    st.markdown("**Identified Risks:**")
                    for risk in supplier['risks']:
                        st.markdown(f"⚠️ {risk}")
                
                # Financial analysis (if available)
                if supplier.get('financials'):
                    st.markdown("---")
                    st.markdown("**Financial Metrics:**")
                    fin = supplier['financials']
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if fin.get('market_cap'):
                            mc = fin['market_cap'] / 1e9
                            st.metric("Market Cap", f"${mc:.1f}B")
                    with col2:
                        if fin.get('profit_margin'):
                            st.metric("Profit Margin", f"{fin['profit_margin']*100:.1f}%")
                    with col3:
                        if fin.get('debt_to_equity'):
                            st.metric("Debt/Equity", f"{fin['debt_to_equity']:.2f}")
                
                # MD&A Analysis (if available)
                if supplier.get('mda_analysis') and supplier['mda_analysis'].get('success'):
                    mda = supplier['mda_analysis']
                    
                    st.markdown("---")
                    st.markdown("**MD&A Analysis (AI-Generated):**")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        health = mda.get('financial_health', 'Unknown')
                        health_color = "🟢" if health == "Healthy" else "🟡" if health == "Concerning" else "🔴"
                        st.markdown(f"**Financial Health:** {health_color} {health}")
                    with col2:
                        outlook = mda.get('forward_outlook', 'Unknown')
                        outlook_color = "🟢" if outlook == "Positive" else "🟡" if outlook == "Neutral" else "🔴"
                        st.markdown(f"**Outlook:** {outlook_color} {outlook}")
                    with col3:
                        reliability = mda.get('reliability_score', 0)
                        st.metric("Reliability", f"{reliability}/10")
                    
                    if mda.get('summary'):
                        st.markdown(f"**Summary:** {mda['summary']}")
                    
                    if mda.get('red_flags'):
                        st.warning("**🚨 Red Flags:**")
                        for flag in mda['red_flags']:
                            st.markdown(f"• {flag}")
                    
                    if mda.get('key_risks'):
                        with st.expander("View detailed risks"):
                            for risk in mda['key_risks']:
                                st.markdown(f"• {risk}")
    else:
        st.error(f"❌ Error: {supplier_result.get('error', 'Unable to analyze suppliers')}")
    
# Disclaimer
st.markdown("---")
st.markdown("""
<div style="background-color: #fff3cd; padding: 1rem; border-radius: 0.5rem;">
    <strong>⚠️ DISCLAIMER</strong><br>
    For educational purposes only. NOT investment advice. 
    Consult a qualified financial advisor before making investment decisions.
</div>
""", unsafe_allow_html=True)
