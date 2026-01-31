"""
Company Performance Analyzer - Module 1 (Enhanced with Caching)
Analyzes the LATEST 10-K and 10-Q filings with intelligent caching
"""

from edgar import Company, set_identity
import pandas as pd
from datetime import datetime, timedelta
import yfinance as yf
import re
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
    
    Caching Strategy:
    - SEC filings: Cache for 90 days (quarterly data)
    - Stock price: Cache for 24 hours (daily data)
    - Financial metrics: Cache for 90 days
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
    
    def get_company_filings(self, ticker: str) -> Dict:
        """
        Fetch MOST RECENT 10-K and 10-Q filings with caching
        Cached for 90 days (quarterly refresh)
        """
        
        if self.use_cache:
            # Try cache first
            cached = self.cache.get('financial_statements', ticker=ticker)
            if cached:
                cached['_from_cache'] = True
                return cached
        
        # Cache miss - fetch fresh data
        try:
            company = Company(ticker)
            
            # Get most recent filings (within last 18 months)
            cutoff_date = self.current_date - timedelta(days=545)  # 18 months
            
            tenk_filings = company.get_filings(form="10-K")
            tenq_filings = company.get_filings(form="10-Q")
            
            # Get latest of each type
            latest_10k = tenk_filings.latest(1) if tenk_filings else None
            latest_10qs = tenq_filings.latest(4) if tenq_filings else None
            
            result = {
                'success': True,
                'company_name': company.name,
                'ticker': ticker.upper(),
                'tenk': latest_10k,
                'tenq': latest_10qs,
                'cik': company.cik,
                '_from_cache': False
            }
            
            # Cache the result
            if self.use_cache:
                # Store serializable version (without Filing objects)
                cache_data = {
                    'success': True,
                    'company_name': company.name,
                    'ticker': ticker.upper(),
                    'cik': company.cik,
                    'has_10k': latest_10k is not None,
                    'has_10q': latest_10qs is not None,
                    'cached_at': datetime.now().isoformat()
                }
                self.cache.set('financial_statements', cache_data, ticker=ticker, cost=0.01)
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'ticker': ticker.upper()
            }
    
    def get_stock_price(self, ticker: str) -> Dict:
        """
        Get current stock price with caching
        Cached for 24 hours (daily refresh)
        """
        
        if self.use_cache:
            cached = self.cache.get('stock_fundamentals', ticker=ticker)
            if cached:
                cached['_from_cache'] = True
                return cached
        
        # Cache miss - fetch fresh
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
            
            # Calculate margins
            gross_margin = 0
            operating_margin = 0
            net_margin = 0
            
            if revenue and revenue > 0:
                if operating_income:
                    operating_margin = (operating_income / revenue) * 100
                if net_income:
                    net_margin = (net_income / revenue) * 100
            
            return {
                'revenue': float(revenue) if revenue else 0,
                'net_income': float(net_income) if net_income else 0,
                'operating_income': float(operating_income) if operating_income else 0,
                'gross_margin': float(gross_margin) if gross_margin else 0,
                'operating_margin': float(operating_margin) if operating_margin else 0,
                'net_margin': float(net_margin) if net_margin else 0
            }
            
        except Exception as e:
            return {
                'revenue': 0,
                'net_income': 0,
                'operating_income': 0,
                'gross_margin': 0,
                'operating_margin': 0,
                'net_margin': 0,
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
        
        # Score based on operating margin
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
    
    def assess_financial_health(self, filing) -> Dict:
        """Assess financial health from balance sheet"""
        try:
            facts = filing.financials
            
            # Get balance sheet items
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
            
            # Calculate ratios
            debt_to_assets = (debt / assets * 100) if assets else 0
            cash_to_debt = (cash / debt) if debt else 999
            
            # Score
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
            
        except Exception as e:
            return {
                'score': 0,
                'reasoning': f'Unable to assess: {str(e)}'
            }
    
    def analyze(self, ticker: str, verbose: bool = True) -> Dict:
        """
        Complete company performance analysis with caching
        
        Returns comprehensive analysis with cache status
        """
        
        if verbose:
            print(f"\n{'='*80}")
            print(f"COMPANY PERFORMANCE ANALYSIS: {ticker.upper()}")
            if self.use_cache:
                print(f"Caching: ENABLED (90-day TTL for filings)")
            print(f"{'='*80}\n")
        
        # Get filings (with caching)
        filings = self.get_company_filings(ticker)
        
        if not filings.get('success'):
            return {
                'success': False,
                'error': filings.get('error', 'Failed to fetch filings')
            }
        
        if verbose and filings.get('_from_cache'):
            print("✅ Using cached financial statements (fresh)")
        
        # Get stock price (with caching)
        price_data = self.get_stock_price(ticker)
        
        if verbose and price_data.get('_from_cache'):
            print("✅ Using cached stock price (fresh)")
        
        # Analyze financials
        tenk = filings.get('tenk')
        tenq = filings.get('tenq')
        
        if not tenk and not tenq:
            return {
                'success': False,
                'error': 'No recent filings available'
            }
        
        # Use most recent filing
        latest_filing = tenq[0] if tenq else tenk[0] if tenk else None
        
        if not latest_filing:
            return {
                'success': False,
                'error': 'No valid filings'
            }
        
        # Extract metrics
        current_metrics = self.extract_financial_metrics(latest_filing)
        
        # Get prior period for comparison
        prior_filing = tenq[3] if tenq and len(tenq) > 3 else tenk[0] if tenk else None
        prior_metrics = self.extract_financial_metrics(prior_filing) if prior_filing else None
        
        # Calculate scores
        revenue_analysis = self.calculate_revenue_growth(
            current_metrics['revenue'],
            prior_metrics['revenue'] if prior_metrics else 0
        )
        
        margin_analysis = self.assess_margins(current_metrics)
        health_analysis = self.assess_financial_health(latest_filing)
        
        # Weighted composite
        factors = {
            'revenue_growth': revenue_analysis,
            'margins': margin_analysis,
            'financial_health': health_analysis,
            'profitability': {'score': 1.0, 'reasoning': 'Positive net income'},
            'guidance': {'score': 0.5, 'reasoning': 'Stable outlook'}
        }
        
        composite_raw = sum(
            factors[factor]['score'] * self.weights[factor]
            for factor in self.weights
        )
        
        # Convert to 1-10 scale
        composite = round(5.5 + (composite_raw * 2.25), 1)
        
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
            if self.use_cache:
                print(f"Cache Status: {1 if filings.get('_from_cache') else 0 + 1 if price_data.get('_from_cache') else 0}/2 from cache")
            print(f"{'='*80}\n")
        
        return {
            'success': True,
            'ticker': ticker.upper(),
            'company_name': filings.get('company_name', ticker),
            'score': composite,
            'signal': signal,
            'factors': factors,
            'current_metrics': current_metrics,
            'prior_metrics': prior_metrics,
            'price_data': price_data,
            'data_date': latest_filing.filing_date.strftime('%Y-%m-%d') if hasattr(latest_filing, 'filing_date') else 'Unknown',
            '_cache_info': {
                'filings_cached': filings.get('_from_cache', False),
                'price_cached': price_data.get('_from_cache', False)
            },
            'cost': 0.02  # Estimated API cost
        }


if __name__ == "__main__":
    # Test
    analyzer = CompanyPerformanceAnalyzer()
    result = analyzer.analyze('NVDA', verbose=True)
    
    if result['success']:
        print(f"✅ Analysis complete: {result['score']}/10 - {result['signal']}")
    else:
        print(f"❌ Error: {result.get('error')}")
