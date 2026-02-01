"""
Company Performance Analyzer - Module 1 (FIXED VERSION)
Properly handles caching by storing extracted metrics, not Filing objects
"""

from edgar import Company, set_identity
import pandas as pd
from datetime import datetime, timedelta
import yfinance as yf
import re
import time
from typing import Dict, Optional

# Import cache manager
try:
    from cache_manager import DataCacheManager
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False
    print("⚠️ cache_manager not found - running without caching")

# Set Edgar identity (required by SEC)
set_identity("Paul Balasubramanian factorimpactai@gmail.com")


class CompanyPerformanceAnalyzer:
    """
    Analyzes company performance from SEC filings with intelligent caching
    
    FIXED: Now caches extracted metrics (not Filing objects)
    """
    
    def __init__(self, use_cache: bool = True):
        """Initialize analyzer with optional caching"""
        self.weights = {
            'revenue_growth': 0.25,
            'profitability': 0.25,
            'margins': 0.20,
            'guidance': 0.15,
            'financial_health': 0.15
        }
        self.current_date = datetime.now()
        self.use_cache = use_cache and CACHE_AVAILABLE
        
        if self.use_cache:
            self.cache = DataCacheManager()
    
    def extract_financial_metrics(self, filing) -> Dict:
        """Extract key financial metrics from filing"""
        try:
            facts = filing.financials
            
            # Revenue
            revenue = facts.get('Revenues', facts.get('RevenueFromContractWithCustomerExcludingAssessedTax', 0))
            if isinstance(revenue, pd.Series):
                revenue = revenue.iloc[0] if len(revenue) > 0 else 0
            
            # Net Income
            net_income = facts.get('NetIncomeLoss', 0)
            if isinstance(net_income, pd.Series):
                net_income = net_income.iloc[0] if len(net_income) > 0 else 0
            
            # Operating Income
            operating_income = facts.get('OperatingIncomeLoss', 0)
            if isinstance(operating_income, pd.Series):
                operating_income = operating_income.iloc[0] if len(operating_income) > 0 else 0
            
            # Assets/Liabilities/Cash/Debt for financial health
            assets = facts.get('Assets', 0)
            liabilities = facts.get('Liabilities', 0)
            cash = facts.get('CashAndCashEquivalentsAtCarryingValue', 0)
            debt = facts.get('LongTermDebt', 0)
            
            if isinstance(assets, pd.Series):
                assets = assets.iloc[0] if len(assets) > 0 else 0
            if isinstance(liabilities, pd.Series):
                liabilities = liabilities.iloc[0] if len(liabilities) > 0 else 0
            if isinstance(cash, pd.Series):
                cash = cash.iloc[0] if len(cash) > 0 else 0
            if isinstance(debt, pd.Series):
                debt = debt.iloc[0] if len(debt) > 0 else 0
            
            # Calculate margins
            operating_margin = 0
            net_margin = 0
            
            if revenue and revenue > 0:
                if operating_income:
                    operating_margin = (operating_income / revenue) * 100
                if net_income:
                    net_margin = (net_income / revenue) * 100
            
            # Calculate ratios
            debt_to_assets = (debt / assets * 100) if assets else 0
            cash_to_debt = (cash / debt) if debt else 999
            
            return {
                'revenue': float(revenue) if revenue else 0,
                'net_income': float(net_income) if net_income else 0,
                'operating_income': float(operating_income) if operating_income else 0,
                'operating_margin': float(operating_margin) if operating_margin else 0,
                'net_margin': float(net_margin) if net_margin else 0,
                'assets': float(assets) if assets else 0,
                'liabilities': float(liabilities) if liabilities else 0,
                'cash': float(cash) if cash else 0,
                'debt': float(debt) if debt else 0,
                'debt_to_assets': float(debt_to_assets),
                'cash_to_debt': float(cash_to_debt) if cash_to_debt < 999 else 999
            }
            
        except Exception as e:
            return {
                'revenue': 0,
                'net_income': 0,
                'operating_income': 0,
                'operating_margin': 0,
                'net_margin': 0,
                'assets': 0,
                'liabilities': 0,
                'cash': 0,
                'debt': 0,
                'debt_to_assets': 0,
                'cash_to_debt': 0,
                'error': str(e)
            }
    
    def get_company_data(self, ticker: str) -> Dict:
        """
        Fetch company data with proper caching
        FIXED: Caches extracted metrics, not Filing objects
        """
        
        # Check cache first
        if self.use_cache:
            cached = self.cache.get('financial_statements', ticker=ticker)
            if cached and cached.get('current_metrics'):
                cached['_from_cache'] = True
                return cached
        
        # Cache miss - fetch fresh data from SEC
        try:
            company = Company(ticker)
            
            # Get most recent filings
            tenk_filings = company.get_filings(form="10-K")
            tenq_filings = company.get_filings(form="10-Q")
            
            # Get latest of each type
            latest_10k = None
            latest_10qs = []
            
            try:
                for f in tenk_filings:
                    latest_10k = f
                    break
            except:
                pass
            
            try:
                count = 0
                for f in tenq_filings:
                    latest_10qs.append(f)
                    count += 1
                    if count >= 4:
                        break
            except:
                pass
            
            if not latest_10k and not latest_10qs:
                return {
                    'success': False,
                    'error': 'No recent filings available',
                    'ticker': ticker.upper()
                }
            
            # Use most recent filing for current metrics
            latest_filing = latest_10qs[0] if latest_10qs else latest_10k
            current_metrics = self.extract_financial_metrics(latest_filing)
            
            # Get prior period for comparison
            prior_filing = latest_10qs[3] if len(latest_10qs) > 3 else latest_10k
            prior_metrics = self.extract_financial_metrics(prior_filing) if prior_filing else None
            
            # Get filing date
            filing_date = 'Unknown'
            try:
                if hasattr(latest_filing, 'filing_date'):
                    filing_date = latest_filing.filing_date.strftime('%Y-%m-%d')
            except:
                pass
            
            result = {
                'success': True,
                'company_name': company.name,
                'ticker': ticker.upper(),
                'cik': company.cik,
                'current_metrics': current_metrics,
                'prior_metrics': prior_metrics,
                'filing_date': filing_date,
                'has_10k': latest_10k is not None,
                'has_10q': len(latest_10qs) > 0,
                '_from_cache': False
            }
            
            # Cache the extracted metrics (NOT the Filing objects)
            if self.use_cache:
                self.cache.set('financial_statements', result, ticker=ticker, cost=0.01)
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'ticker': ticker.upper()
            }
    
    def get_stock_price(self, ticker: str) -> Dict:
        """Get current stock price with caching"""
        
        if self.use_cache:
            cached = self.cache.get('stock_fundamentals', ticker=ticker)
            if cached:
                cached['_from_cache'] = True
                return cached
        
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            result = {
                'success': True,
                'price': info.get('currentPrice', info.get('regularMarketPrice', 0)),
                'market_cap': info.get('marketCap', 0),
                'pe_ratio': info.get('trailingPE', 0),
                'forward_pe': info.get('forwardPE', 0),
                '_from_cache': False
            }
            
            if self.use_cache:
                self.cache.set('stock_fundamentals', result, ticker=ticker, cost=0.001)
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def calculate_revenue_growth(self, current_revenue: float, prior_revenue: float) -> Dict:
        """Calculate revenue growth score"""
        if not prior_revenue or prior_revenue == 0:
            return {'score': 0, 'growth_rate': 0, 'reasoning': 'No prior revenue data'}
        
        growth_rate = ((current_revenue - prior_revenue) / prior_revenue) * 100
        
        if growth_rate >= 20:
            score = 2.0
            reasoning = f"Exceptional growth: {growth_rate:.1f}% YoY"
        elif growth_rate >= 10:
            score = 1.5
            reasoning = f"Strong growth: {growth_rate:.1f}% YoY"
        elif growth_rate >= 5:
            score = 1.0
            reasoning = f"Solid growth: {growth_rate:.1f}% YoY"
        elif growth_rate >= 0:
            score = 0.5
            reasoning = f"Modest growth: {growth_rate:.1f}% YoY"
        elif growth_rate >= -5:
            score = -0.5
            reasoning = f"Slight decline: {growth_rate:.1f}% YoY"
        else:
            score = -1.5
            reasoning = f"Significant decline: {growth_rate:.1f}% YoY"
        
        return {
            'score': score,
            'growth_rate': round(growth_rate, 2),
            'reasoning': reasoning
        }
    
    def assess_margins(self, metrics: Dict) -> Dict:
        """Assess profitability margins"""
        operating_margin = metrics.get('operating_margin', 0)
        net_margin = metrics.get('net_margin', 0)
        
        if operating_margin >= 30:
            score = 2.0
            reasoning = f"Exceptional margins: {operating_margin:.1f}% operating"
        elif operating_margin >= 20:
            score = 1.5
            reasoning = f"Strong margins: {operating_margin:.1f}% operating"
        elif operating_margin >= 10:
            score = 1.0
            reasoning = f"Healthy margins: {operating_margin:.1f}% operating"
        elif operating_margin >= 5:
            score = 0.5
            reasoning = f"Modest margins: {operating_margin:.1f}% operating"
        elif operating_margin >= 0:
            score = 0
            reasoning = f"Breakeven: {operating_margin:.1f}% operating"
        else:
            score = -1.5
            reasoning = f"Unprofitable: {operating_margin:.1f}% operating"
        
        return {
            'score': score,
            'operating_margin': round(operating_margin, 2),
            'net_margin': round(net_margin, 2),
            'reasoning': reasoning
        }
    
    def assess_financial_health(self, metrics: Dict) -> Dict:
        """Assess financial health from cached metrics"""
        debt_to_assets = metrics.get('debt_to_assets', 0)
        cash_to_debt = metrics.get('cash_to_debt', 0)
        cash = metrics.get('cash', 0)
        debt = metrics.get('debt', 0)
        
        if debt_to_assets < 20 and cash > debt:
            score = 2.0
            reasoning = f"Excellent: {debt_to_assets:.1f}% debt/assets, {cash_to_debt:.1f}x cash coverage"
        elif debt_to_assets < 40:
            score = 1.0
            reasoning = f"Healthy: {debt_to_assets:.1f}% debt/assets"
        elif debt_to_assets < 60:
            score = 0
            reasoning = f"Moderate: {debt_to_assets:.1f}% debt/assets"
        else:
            score = -1.0
            reasoning = f"Concerning: {debt_to_assets:.1f}% debt/assets"
        
        return {
            'score': score,
            'debt_to_assets': round(debt_to_assets, 2),
            'cash_to_debt': round(cash_to_debt, 2) if cash_to_debt < 999 else 999,
            'reasoning': reasoning
        }
    
    def analyze(self, ticker: str, verbose: bool = True) -> Dict:
        """Complete company performance analysis with caching"""
        
        if verbose:
            print(f"\n{'='*80}")
            print(f"COMPANY PERFORMANCE ANALYSIS: {ticker.upper()}")
            if self.use_cache:
                print(f"Caching: ENABLED (90-day TTL for filings)")
            print(f"{'='*80}\n")
        
        # Get company data (with caching)
        company_data = self.get_company_data(ticker)
        
        if not company_data.get('success'):
            return {
                'success': False,
                'error': company_data.get('error', 'Failed to fetch company data')
            }
        
        if verbose and company_data.get('_from_cache'):
            print("✅ Using cached financial statements (fresh)")
        
        # Get stock price (with caching)
        price_data = self.get_stock_price(ticker)
        
        if verbose and price_data.get('_from_cache'):
            print("✅ Using cached stock price (fresh)")
        
        # Use cached metrics
        current_metrics = company_data.get('current_metrics', {})
        prior_metrics = company_data.get('prior_metrics', {})
        
        if not current_metrics or current_metrics.get('revenue', 0) == 0:
            return {
                'success': False,
                'error': 'No financial data available'
            }
        
        # Calculate scores from cached metrics
        revenue_analysis = self.calculate_revenue_growth(
            current_metrics.get('revenue', 0),
            prior_metrics.get('revenue', 0) if prior_metrics else 0
        )
        
        margin_analysis = self.assess_margins(current_metrics)
        health_analysis = self.assess_financial_health(current_metrics)
        
        # Weighted composite
        factors = {
            'revenue_growth': revenue_analysis,
            'margins': margin_analysis,
            'financial_health': health_analysis,
            'profitability': {'score': 1.0 if current_metrics.get('net_income', 0) > 0 else -0.5, 
                            'reasoning': 'Positive net income' if current_metrics.get('net_income', 0) > 0 else 'Net loss'},
            'guidance': {'score': 0.5, 'reasoning': 'Stable outlook'}
        }
        
        composite_raw = sum(
            factors[factor]['score'] * self.weights[factor]
            for factor in self.weights
        )
        
        # Convert to 1-10 scale
        composite = round(5.5 + (composite_raw * 2.25), 1)
        composite = max(1, min(10, composite))  # Clamp to 1-10
        
        # Determine signal
        if composite >= 8.5:
            signal = "STRONG BUY"
        elif composite >= 7.0:
            signal = "BUY"
        elif composite >= 5.5:
            signal = "HOLD"
        else:
            signal = "SELL"
        
        if verbose:
            print(f"\n{'='*80}")
            print(f"COMPANY SCORE: {composite}/10")
            print(f"SIGNAL: {signal}")
            print(f"{'='*80}")
            cache_hits = (1 if company_data.get('_from_cache') else 0) + (1 if price_data.get('_from_cache') else 0)
            print(f"Cache Status: {cache_hits}/2 from cache")
            print(f"{'='*80}\n")
        
        return {
            'success': True,
            'ticker': ticker.upper(),
            'company_name': company_data.get('company_name', ticker),
            'score': composite,
            'signal': signal,
            'factors': factors,
            'current_metrics': current_metrics,
            'prior_metrics': prior_metrics,
            'price_data': price_data,
            'data_date': company_data.get('filing_date', 'Unknown'),
            '_cache_info': {
                'filings_cached': company_data.get('_from_cache', False),
                'price_cached': price_data.get('_from_cache', False)
            },
            'cost': 0.02
        }


if __name__ == "__main__":
    analyzer = CompanyPerformanceAnalyzer()
    result = analyzer.analyze('NVDA', verbose=True)
    
    if result['success']:
        print(f"✅ Analysis complete: {result['score']}/10 - {result['signal']}")
    else:
        print(f"❌ Error: {result.get('error')}")
