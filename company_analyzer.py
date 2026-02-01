"""
Company Performance Analyzer - Module 1 (ROBUST VERSION)
Uses yfinance as PRIMARY data source (more reliable than parsing SEC filings)
Falls back gracefully when data is unavailable
"""

import pandas as pd
from datetime import datetime, timedelta
import yfinance as yf
from typing import Dict, Optional

# Import cache manager
try:
    from cache_manager import DataCacheManager
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False
    print("⚠️ cache_manager not found - running without caching")

# Optional: Edgar for filing dates only
try:
    from edgar import Company, set_identity
    set_identity("Paul Balasubramanian factorimpactai@gmail.com")
    EDGAR_AVAILABLE = True
except ImportError:
    EDGAR_AVAILABLE = False


class CompanyPerformanceAnalyzer:
    """
    Analyzes company performance using yfinance (primary) + SEC filings (backup)
    
    Much more reliable than parsing SEC XBRL directly
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
    
    def get_financial_data(self, ticker: str) -> Dict:
        """
        Get financial data from yfinance (primary source)
        Much more reliable than parsing SEC filings
        """
        
        # Check cache first
        if self.use_cache:
            cached = self.cache.get('company_financials', ticker=ticker)
            if cached and cached.get('revenue'):
                cached['_from_cache'] = True
                return cached
        
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Get quarterly financials
            quarterly_financials = stock.quarterly_financials
            quarterly_income = stock.quarterly_income_stmt
            balance_sheet = stock.quarterly_balance_sheet
            
            # Extract key metrics
            result = {
                'success': True,
                'ticker': ticker.upper(),
                'company_name': info.get('longName', info.get('shortName', ticker)),
                '_from_cache': False
            }
            
            # === REVENUE & GROWTH ===
            revenue = None
            revenue_prev = None
            revenue_growth = None
            
            # Try quarterly income statement first
            if quarterly_income is not None and not quarterly_income.empty:
                try:
                    if 'Total Revenue' in quarterly_income.index:
                        revenue = quarterly_income.loc['Total Revenue'].iloc[0]
                        if len(quarterly_income.columns) > 4:
                            revenue_prev = quarterly_income.loc['Total Revenue'].iloc[4]  # YoY
                        elif len(quarterly_income.columns) > 1:
                            revenue_prev = quarterly_income.loc['Total Revenue'].iloc[-1]
                except:
                    pass
            
            # Fallback to info
            if revenue is None:
                revenue = info.get('totalRevenue', info.get('revenue', 0))
            
            # Calculate growth
            if revenue and revenue_prev and revenue_prev != 0:
                revenue_growth = ((revenue - revenue_prev) / abs(revenue_prev)) * 100
            else:
                revenue_growth = info.get('revenueGrowth', 0)
                if revenue_growth:
                    revenue_growth = revenue_growth * 100  # Convert to percentage
            
            result['revenue'] = float(revenue) if revenue else 0
            result['revenue_prev'] = float(revenue_prev) if revenue_prev else 0
            result['revenue_growth'] = float(revenue_growth) if revenue_growth else 0
            
            # === PROFITABILITY ===
            net_income = None
            operating_income = None
            
            if quarterly_income is not None and not quarterly_income.empty:
                try:
                    if 'Net Income' in quarterly_income.index:
                        net_income = quarterly_income.loc['Net Income'].iloc[0]
                    if 'Operating Income' in quarterly_income.index:
                        operating_income = quarterly_income.loc['Operating Income'].iloc[0]
                except:
                    pass
            
            if net_income is None:
                net_income = info.get('netIncomeToCommon', info.get('netIncome', 0))
            
            result['net_income'] = float(net_income) if net_income else 0
            result['operating_income'] = float(operating_income) if operating_income else 0
            
            # === MARGINS ===
            gross_margin = info.get('grossMargins', 0)
            operating_margin = info.get('operatingMargins', 0)
            profit_margin = info.get('profitMargins', 0)
            
            # Convert to percentages if they're decimals
            if gross_margin and gross_margin < 1:
                gross_margin = gross_margin * 100
            if operating_margin and operating_margin < 1:
                operating_margin = operating_margin * 100
            if profit_margin and profit_margin < 1:
                profit_margin = profit_margin * 100
            
            result['gross_margin'] = float(gross_margin) if gross_margin else 0
            result['operating_margin'] = float(operating_margin) if operating_margin else 0
            result['net_margin'] = float(profit_margin) if profit_margin else 0
            
            # === FINANCIAL HEALTH ===
            total_debt = info.get('totalDebt', 0)
            total_cash = info.get('totalCash', 0)
            total_assets = None
            
            if balance_sheet is not None and not balance_sheet.empty:
                try:
                    if 'Total Assets' in balance_sheet.index:
                        total_assets = balance_sheet.loc['Total Assets'].iloc[0]
                except:
                    pass
            
            if total_assets is None:
                total_assets = info.get('totalAssets', 0)
            
            debt_to_equity = info.get('debtToEquity', 0)
            current_ratio = info.get('currentRatio', 0)
            
            result['total_debt'] = float(total_debt) if total_debt else 0
            result['total_cash'] = float(total_cash) if total_cash else 0
            result['total_assets'] = float(total_assets) if total_assets else 0
            result['debt_to_equity'] = float(debt_to_equity) if debt_to_equity else 0
            result['current_ratio'] = float(current_ratio) if current_ratio else 0
            
            # Calculate debt to assets
            if total_assets and total_assets > 0:
                result['debt_to_assets'] = (total_debt / total_assets) * 100 if total_debt else 0
            else:
                result['debt_to_assets'] = 0
            
            # Cash coverage
            if total_debt and total_debt > 0:
                result['cash_to_debt'] = total_cash / total_debt if total_cash else 0
            else:
                result['cash_to_debt'] = 999  # No debt = infinite coverage
            
            # === STOCK DATA ===
            result['price'] = info.get('currentPrice', info.get('regularMarketPrice', 0))
            result['market_cap'] = info.get('marketCap', 0)
            result['pe_ratio'] = info.get('trailingPE', 0)
            result['forward_pe'] = info.get('forwardPE', 0)
            result['beta'] = info.get('beta', 1.0)
            
            # === DATA DATE ===
            result['data_date'] = datetime.now().strftime('%Y-%m-%d')
            
            # Try to get latest filing date from Edgar
            if EDGAR_AVAILABLE:
                try:
                    company = Company(ticker)
                    filings = company.get_filings(form="10-Q")
                    for f in filings:
                        result['data_date'] = str(f.filing_date)
                        break
                except:
                    pass
            
            # Cache the result
            if self.use_cache and result.get('revenue', 0) > 0:
                self.cache.set('company_financials', result, ticker=ticker, cost=0.01)
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'ticker': ticker.upper()
            }
    
    def calculate_revenue_growth_score(self, growth_rate: float) -> Dict:
        """Calculate revenue growth score"""
        if growth_rate is None:
            return {'score': 0, 'growth_rate': 0, 'reasoning': 'No growth data'}
        
        if growth_rate >= 25:
            score = 2.0
            reasoning = f"Exceptional growth: {growth_rate:.1f}%"
        elif growth_rate >= 15:
            score = 1.5
            reasoning = f"Strong growth: {growth_rate:.1f}%"
        elif growth_rate >= 8:
            score = 1.0
            reasoning = f"Solid growth: {growth_rate:.1f}%"
        elif growth_rate >= 0:
            score = 0.5
            reasoning = f"Modest growth: {growth_rate:.1f}%"
        elif growth_rate >= -5:
            score = -0.5
            reasoning = f"Slight decline: {growth_rate:.1f}%"
        else:
            score = -1.5
            reasoning = f"Significant decline: {growth_rate:.1f}%"
        
        return {
            'score': score,
            'growth_rate': round(growth_rate, 2),
            'reasoning': reasoning
        }
    
    def assess_margins(self, data: Dict) -> Dict:
        """Assess profitability margins"""
        operating_margin = data.get('operating_margin', 0)
        net_margin = data.get('net_margin', 0)
        
        # Use operating margin as primary metric
        margin = operating_margin if operating_margin else net_margin
        
        if margin >= 30:
            score = 2.0
            reasoning = f"Exceptional margins: {margin:.1f}%"
        elif margin >= 20:
            score = 1.5
            reasoning = f"Strong margins: {margin:.1f}%"
        elif margin >= 12:
            score = 1.0
            reasoning = f"Healthy margins: {margin:.1f}%"
        elif margin >= 5:
            score = 0.5
            reasoning = f"Modest margins: {margin:.1f}%"
        elif margin >= 0:
            score = 0
            reasoning = f"Breakeven: {margin:.1f}%"
        else:
            score = -1.5
            reasoning = f"Unprofitable: {margin:.1f}%"
        
        return {
            'score': score,
            'operating_margin': round(operating_margin, 2),
            'net_margin': round(net_margin, 2),
            'reasoning': reasoning
        }
    
    def assess_financial_health(self, data: Dict) -> Dict:
        """Assess financial health"""
        debt_to_assets = data.get('debt_to_assets', 0)
        cash_to_debt = data.get('cash_to_debt', 0)
        current_ratio = data.get('current_ratio', 0)
        debt_to_equity = data.get('debt_to_equity', 0)
        
        # Score based on multiple factors
        score = 0.0
        reasons = []
        
        # Debt level
        if debt_to_assets < 20:
            score += 1.0
            reasons.append(f"Low debt ({debt_to_assets:.0f}% of assets)")
        elif debt_to_assets < 40:
            score += 0.5
            reasons.append(f"Moderate debt ({debt_to_assets:.0f}% of assets)")
        elif debt_to_assets < 60:
            reasons.append(f"High debt ({debt_to_assets:.0f}% of assets)")
        else:
            score -= 1.0
            reasons.append(f"Very high debt ({debt_to_assets:.0f}% of assets)")
        
        # Cash position
        if cash_to_debt > 2:
            score += 1.0
            reasons.append("Strong cash position")
        elif cash_to_debt > 1:
            score += 0.5
            reasons.append("Adequate cash")
        elif cash_to_debt > 0.5:
            pass  # Neutral
        else:
            score -= 0.5
            reasons.append("Low cash coverage")
        
        # Cap score
        score = max(-2.0, min(2.0, score))
        
        return {
            'score': score,
            'debt_to_assets': round(debt_to_assets, 2),
            'cash_to_debt': round(cash_to_debt, 2) if cash_to_debt < 999 else 999,
            'current_ratio': round(current_ratio, 2),
            'reasoning': "; ".join(reasons) if reasons else "Neutral financial health"
        }
    
    def analyze(self, ticker: str, verbose: bool = True) -> Dict:
        """Complete company performance analysis"""
        
        if verbose:
            print(f"\n{'='*80}")
            print(f"COMPANY PERFORMANCE ANALYSIS: {ticker.upper()}")
            if self.use_cache:
                print(f"Caching: ENABLED")
            print(f"{'='*80}\n")
        
        # Get financial data (primarily from yfinance)
        data = self.get_financial_data(ticker)
        
        if not data.get('success', False):
            return {
                'success': False,
                'error': data.get('error', 'Failed to fetch financial data')
            }
        
        if verbose and data.get('_from_cache'):
            print("✅ Using cached financial data")
        
        # Check if we have minimum required data
        if data.get('revenue', 0) == 0 and data.get('market_cap', 0) == 0:
            return {
                'success': False,
                'error': 'Insufficient financial data available for this ticker'
            }
        
        # Calculate scores
        revenue_analysis = self.calculate_revenue_growth_score(data.get('revenue_growth', 0))
        margin_analysis = self.assess_margins(data)
        health_analysis = self.assess_financial_health(data)
        
        # Profitability score
        net_income = data.get('net_income', 0)
        if net_income > 0:
            profitability = {'score': 1.0, 'reasoning': 'Profitable company'}
        elif net_income == 0:
            profitability = {'score': 0, 'reasoning': 'Breakeven'}
        else:
            profitability = {'score': -1.0, 'reasoning': 'Net loss'}
        
        # Guidance (placeholder - would need earnings call analysis)
        guidance = {'score': 0.5, 'reasoning': 'Assumed stable outlook'}
        
        # Weighted composite
        factors = {
            'revenue_growth': revenue_analysis,
            'margins': margin_analysis,
            'financial_health': health_analysis,
            'profitability': profitability,
            'guidance': guidance
        }
        
        composite_raw = sum(
            factors[factor]['score'] * self.weights[factor]
            for factor in self.weights
        )
        
        # Convert to 1-10 scale
        composite = round(5.5 + (composite_raw * 2.25), 1)
        composite = max(1, min(10, composite))
        
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
            print(f"{'='*80}\n")
        
        return {
            'success': True,
            'ticker': ticker.upper(),
            'company_name': data.get('company_name', ticker),
            'score': composite,
            'signal': signal,
            'factors': factors,
            'current_metrics': {
                'revenue': data.get('revenue', 0),
                'revenue_growth': data.get('revenue_growth', 0),
                'net_income': data.get('net_income', 0),
                'operating_margin': data.get('operating_margin', 0),
                'net_margin': data.get('net_margin', 0),
                'debt_to_assets': data.get('debt_to_assets', 0),
                'cash_to_debt': data.get('cash_to_debt', 0)
            },
            'price_data': {
                'price': data.get('price', 0),
                'market_cap': data.get('market_cap', 0),
                'pe_ratio': data.get('pe_ratio', 0),
                'beta': data.get('beta', 1.0)
            },
            'data_date': data.get('data_date', 'Unknown'),
            '_cache_info': {
                'from_cache': data.get('_from_cache', False)
            },
            'cost': 0.02
        }


if __name__ == "__main__":
    analyzer = CompanyPerformanceAnalyzer()
    result = analyzer.analyze('NVDA', verbose=True)
    
    if result['success']:
        print(f"✅ Analysis complete: {result['score']}/10 - {result['signal']}")
        print(f"Revenue: ${result['current_metrics']['revenue']:,.0f}")
        print(f"Revenue Growth: {result['current_metrics']['revenue_growth']:.1f}%")
        print(f"Operating Margin: {result['current_metrics']['operating_margin']:.1f}%")
    else:
        print(f"❌ Error: {result.get('error')}")
