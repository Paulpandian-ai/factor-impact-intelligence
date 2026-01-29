"""
Company Performance Analyzer - Module 1
Analyzes 10-K and 10-Q filings to assess company performance
"""

from edgar import Company, set_identity
import pandas as pd
from datetime import datetime, timedelta
import yfinance as yf
import re

# Set Edgar identity (required by SEC)
set_identity("Paul Balasubramanian paul@example.com")


class CompanyPerformanceAnalyzer:
    """Analyzes company performance from SEC filings"""
    
    def __init__(self):
        self.weights = {
            'revenue_growth': 0.25,
            'profitability': 0.25,
            'margins': 0.20,
            'guidance': 0.15,
            'financial_health': 0.15
        }
    
    def get_company_filings(self, ticker: str):
        """Fetch recent 10-K and 10-Q filings"""
        try:
            company = Company(ticker)
            
            # Get recent filings
            tenk = company.get_filings(form="10-K").latest(1)
            tenq = company.get_filings(form="10-Q").latest(2)
            
            return {
                'success': True,
                'company_name': company.name,
                'ticker': ticker.upper(),
                'tenk': tenk,
                'tenq': tenq,
                'cik': company.cik
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'ticker': ticker.upper()
            }
    
    def extract_financial_metrics(self, ticker: str):
        """Extract key financial metrics using yfinance"""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Get financials
            income_stmt = stock.quarterly_financials
            balance_sheet = stock.quarterly_balance_sheet
            
            if income_stmt.empty:
                return None
            
            # Extract key metrics
            metrics = {
                'revenue': income_stmt.loc['Total Revenue'].iloc[0] if 'Total Revenue' in income_stmt.index else None,
                'revenue_prev': income_stmt.loc['Total Revenue'].iloc[1] if 'Total Revenue' in income_stmt.index and len(income_stmt.columns) > 1 else None,
                'net_income': income_stmt.loc['Net Income'].iloc[0] if 'Net Income' in income_stmt.index else None,
                'net_income_prev': income_stmt.loc['Net Income'].iloc[1] if 'Net Income' in income_stmt.index and len(income_stmt.columns) > 1 else None,
                'gross_profit': income_stmt.loc['Gross Profit'].iloc[0] if 'Gross Profit' in income_stmt.index else None,
                'operating_income': income_stmt.loc['Operating Income'].iloc[0] if 'Operating Income' in income_stmt.index else None,
                'market_cap': info.get('marketCap'),
                'pe_ratio': info.get('trailingPE'),
                'profit_margin': info.get('profitMargins'),
                'roe': info.get('returnOnEquity'),
                'debt_to_equity': info.get('debtToEquity'),
                'current_ratio': info.get('currentRatio'),
                'forward_eps': info.get('forwardEps'),
                'trailing_eps': info.get('trailingEps')
            }
            
            return metrics
        except Exception as e:
            print(f"Error extracting metrics: {e}")
            return None
    
    def score_revenue_growth(self, metrics):
        """Score revenue growth trends"""
        if not metrics or not metrics.get('revenue') or not metrics.get('revenue_prev'):
            return 0, "Unable to assess revenue growth"
        
        try:
            revenue = float(metrics['revenue'])
            revenue_prev = float(metrics['revenue_prev'])
            
            growth = ((revenue - revenue_prev) / revenue_prev) * 100
            
            if growth > 20:
                score = 2.0
                status = "EXCELLENT"
            elif growth > 10:
                score = 1.5
                status = "STRONG"
            elif growth > 5:
                score = 1.0
                status = "GOOD"
            elif growth > 0:
                score = 0.5
                status = "MODEST"
            elif growth > -5:
                score = -0.5
                status = "DECLINING"
            else:
                score = -2.0
                status = "POOR"
            
            reasoning = f"Revenue growth: {growth:.1f}% QoQ ({status})"
            return score, reasoning
        except:
            return 0, "Unable to calculate revenue growth"
    
    def score_profitability(self, metrics):
        """Score profitability metrics"""
        if not metrics:
            return 0, "Unable to assess profitability"
        
        try:
            net_income = metrics.get('net_income')
            net_income_prev = metrics.get('net_income_prev')
            
            if not net_income or not net_income_prev:
                return 0, "Insufficient profitability data"
            
            net_income = float(net_income)
            net_income_prev = float(net_income_prev)
            
            # Check profitability
            if net_income <= 0:
                score = -2.0
                status = "UNPROFITABLE"
            else:
                profit_growth = ((net_income - net_income_prev) / abs(net_income_prev)) * 100
                
                if profit_growth > 25:
                    score = 2.0
                    status = "EXCELLENT"
                elif profit_growth > 15:
                    score = 1.5
                    status = "STRONG"
                elif profit_growth > 5:
                    score = 1.0
                    status = "GOOD"
                elif profit_growth > 0:
                    score = 0.5
                    status = "MODEST"
                else:
                    score = -1.0
                    status = "DECLINING"
            
            reasoning = f"Profitability: {status}"
            return score, reasoning
        except Exception as e:
            return 0, "Unable to calculate profitability"
    
    def score_margins(self, metrics):
        """Score profit margins"""
        if not metrics:
            return 0, "Unable to assess margins"
        
        try:
            profit_margin = metrics.get('profit_margin')
            
            if not profit_margin:
                return 0, "Margin data unavailable"
            
            profit_margin = float(profit_margin) * 100
            
            if profit_margin > 20:
                score = 2.0
                status = "EXCELLENT"
            elif profit_margin > 15:
                score = 1.5
                status = "STRONG"
            elif profit_margin > 10:
                score = 1.0
                status = "GOOD"
            elif profit_margin > 5:
                score = 0.5
                status = "AVERAGE"
            elif profit_margin > 0:
                score = 0
                status = "LOW"
            else:
                score = -2.0
                status = "NEGATIVE"
            
            reasoning = f"Profit margin: {profit_margin:.1f}% ({status})"
            return score, reasoning
        except:
            return 0, "Unable to calculate margins"
    
    def score_financial_health(self, metrics):
        """Score overall financial health"""
        if not metrics:
            return 0, "Unable to assess financial health"
        
        score = 0
        factors = []
        
        try:
            # Current ratio (liquidity)
            current_ratio = metrics.get('current_ratio')
            if current_ratio:
                if current_ratio > 2.0:
                    score += 0.5
                    factors.append("Strong liquidity")
                elif current_ratio < 1.0:
                    score -= 0.5
                    factors.append("Weak liquidity")
            
            # Debt to equity
            debt_to_equity = metrics.get('debt_to_equity')
            if debt_to_equity:
                if debt_to_equity < 0.5:
                    score += 0.5
                    factors.append("Low debt")
                elif debt_to_equity > 2.0:
                    score -= 0.5
                    factors.append("High debt")
            
            # ROE
            roe = metrics.get('roe')
            if roe:
                if roe > 0.20:
                    score += 1.0
                    factors.append("Excellent ROE")
                elif roe > 0.15:
                    score += 0.5
                    factors.append("Good ROE")
                elif roe < 0.05:
                    score -= 0.5
                    factors.append("Weak ROE")
            
            score = max(-2.0, min(2.0, score))
            reasoning = "Financial health: " + ", ".join(factors) if factors else "Mixed indicators"
            
            return score, reasoning
        except:
            return 0, "Unable to assess financial health"
    
    def score_guidance(self, metrics):
        """Score based on forward guidance (using forward EPS as proxy)"""
        if not metrics:
            return 0, "Unable to assess guidance"
        
        try:
            forward_eps = metrics.get('forward_eps')
            trailing_eps = metrics.get('trailing_eps')
            
            if not forward_eps or not trailing_eps:
                return 0, "Guidance data unavailable"
            
            eps_growth = ((forward_eps - trailing_eps) / abs(trailing_eps)) * 100
            
            if eps_growth > 20:
                score = 2.0
                status = "VERY POSITIVE"
            elif eps_growth > 10:
                score = 1.5
                status = "POSITIVE"
            elif eps_growth > 5:
                score = 1.0
                status = "MODEST GROWTH"
            elif eps_growth > 0:
                score = 0.5
                status = "SLIGHT GROWTH"
            elif eps_growth > -5:
                score = -0.5
                status = "SLIGHT DECLINE"
            else:
                score = -1.5
                status = "NEGATIVE"
            
            reasoning = f"Forward guidance: {status} (EPS growth: {eps_growth:.1f}%)"
            return score, reasoning
        except:
            return 0, "Unable to assess guidance"
    
    def analyze(self, ticker: str, verbose: bool = True):
        """Perform complete company analysis"""
        if verbose:
            print(f"\n{'='*80}")
            print(f"COMPANY PERFORMANCE ANALYSIS: {ticker.upper()}")
            print(f"{'='*80}\n")
        
        # Get financial metrics
        metrics = self.extract_financial_metrics(ticker)
        
        if not metrics:
            return {
                'success': False,
                'error': 'Unable to fetch financial data',
                'ticker': ticker.upper()
            }
        
        # Score each factor
        rev_score, rev_reasoning = self.score_revenue_growth(metrics)
        prof_score, prof_reasoning = self.score_profitability(metrics)
        margin_score, margin_reasoning = self.score_margins(metrics)
        health_score, health_reasoning = self.score_financial_health(metrics)
        guidance_score, guidance_reasoning = self.score_guidance(metrics)
        
        if verbose:
            print(f"📊 Revenue Growth: {rev_score:+.1f}/2.0")
            print(f"   {rev_reasoning}\n")
            print(f"💰 Profitability: {prof_score:+.1f}/2.0")
            print(f"   {prof_reasoning}\n")
            print(f"📈 Margins: {margin_score:+.1f}/2.0")
            print(f"   {margin_reasoning}\n")
            print(f"🏥 Financial Health: {health_score:+.1f}/2.0")
            print(f"   {health_reasoning}\n")
            print(f"🎯 Guidance: {guidance_score:+.1f}/2.0")
            print(f"   {guidance_reasoning}\n")
        
        # Calculate weighted composite
        weighted = (
            rev_score * self.weights['revenue_growth'] +
            prof_score * self.weights['profitability'] +
            margin_score * self.weights['margins'] +
            health_score * self.weights['financial_health'] +
            guidance_score * self.weights['guidance']
        )
        
        # Convert to 1-10 scale
        composite = round(5.5 + (weighted * 2.25), 1)
        
        # Get recommendation
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
        
        if verbose:
            print(f"{'='*80}")
            print(f"COMPANY SCORE: {composite}/10")
            print(f"RECOMMENDATION: {signal}")
            print(f"{'='*80}\n")
        
        return {
            'success': True,
            'ticker': ticker.upper(),
            'score': composite,
            'signal': signal,
            'factors': {
                'revenue_growth': {'score': rev_score, 'reasoning': rev_reasoning},
                'profitability': {'score': prof_score, 'reasoning': prof_reasoning},
                'margins': {'score': margin_score, 'reasoning': margin_reasoning},
                'financial_health': {'score': health_score, 'reasoning': health_reasoning},
                'guidance': {'score': guidance_score, 'reasoning': guidance_reasoning}
            },
            'metrics': metrics
        }


# Test function
if __name__ == "__main__":
    analyzer = CompanyPerformanceAnalyzer()
    result = analyzer.analyze("NVDA")
    print(f"\nFinal Score: {result['score']}/10")
    print(f"Recommendation: {result['signal']}")
