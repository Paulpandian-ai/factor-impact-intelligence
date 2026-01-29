"""
Company Performance Analyzer - Module 1 (Updated for 2026)
Analyzes the LATEST 10-K and 10-Q filings with timestamp verification
"""

from edgar import Company, set_identity
import pandas as pd
from datetime import datetime, timedelta
import yfinance as yf
import re

# Set Edgar identity (required by SEC)
set_identity("Paul Balasubramanian factorimpactai@gmail.com")


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
        self.current_date = datetime.now()
    
    def get_company_filings(self, ticker: str):
        """Fetch MOST RECENT 10-K and 10-Q filings"""
        try:
            company = Company(ticker)
            
            # Get most recent filings (within last 18 months)
            cutoff_date = self.current_date - timedelta(days=545)  # 18 months
            
            tenk_filings = company.get_filings(form="10-K")
            tenq_filings = company.get_filings(form="10-Q")
            
            # Get latest of each type
            latest_10k = tenk_filings.latest(1) if tenk_filings else None
            latest_10qs = tenq_filings.latest(4) if tenq_filings else None  # Last 4 quarters
            
            return {
                'success': True,
                'company_name': company.name,
                'ticker': ticker.upper(),
                'tenk': latest_10k,
                'tenq': latest_10qs,
                'cik': company.cik
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'ticker': ticker.upper()
            }
    
    def extract_financial_metrics(self, ticker: str):
        """Extract LATEST financial metrics with timestamps"""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Get LATEST quarterly financials
            income_stmt = stock.quarterly_financials
            balance_sheet = stock.quarterly_balance_sheet
            cashflow = stock.quarterly_cashflow
            
            if income_stmt.empty:
                return None
            
            # Get the dates of the financial statements
            latest_quarter = income_stmt.columns[0]
            prev_quarter = income_stmt.columns[1] if len(income_stmt.columns) > 1 else None
            
            # Check data freshness (warn if older than 6 months)
            data_age = (self.current_date - latest_quarter).days
            is_stale = data_age > 180
            
            # Extract key metrics from LATEST quarter
            metrics = {
                # Timestamps
                'latest_quarter_date': latest_quarter,
                'prev_quarter_date': prev_quarter,
                'data_age_days': data_age,
                'is_stale': is_stale,
                'last_updated': self.current_date.strftime('%Y-%m-%d'),
                
                # Revenue
                'revenue': income_stmt.loc['Total Revenue'].iloc[0] if 'Total Revenue' in income_stmt.index else None,
                'revenue_prev': income_stmt.loc['Total Revenue'].iloc[1] if 'Total Revenue' in income_stmt.index and len(income_stmt.columns) > 1 else None,
                
                # Profitability
                'net_income': income_stmt.loc['Net Income'].iloc[0] if 'Net Income' in income_stmt.index else None,
                'net_income_prev': income_stmt.loc['Net Income'].iloc[1] if 'Net Income' in income_stmt.index and len(income_stmt.columns) > 1 else None,
                'gross_profit': income_stmt.loc['Gross Profit'].iloc[0] if 'Gross Profit' in income_stmt.index else None,
                'operating_income': income_stmt.loc['Operating Income'].iloc[0] if 'Operating Income' in income_stmt.index else None,
                
                # Margins & Ratios (from latest data)
                'market_cap': info.get('marketCap'),
                'pe_ratio': info.get('trailingPE'),
                'profit_margin': info.get('profitMargins'),
                'roe': info.get('returnOnEquity'),
                'debt_to_equity': info.get('debtToEquity'),
                'current_ratio': info.get('currentRatio'),
                
                # Forward guidance
                'forward_eps': info.get('forwardEps'),
                'trailing_eps': info.get('trailingEps'),
                
                # Free Cash Flow (important metric)
                'free_cash_flow': cashflow.loc['Free Cash Flow'].iloc[0] if 'Free Cash Flow' in cashflow.index else None,
            }
            
            return metrics
        except Exception as e:
            print(f"Error extracting metrics: {e}")
            return None
    
    def format_quarter_date(self, date):
        """Format quarter date nicely"""
        if pd.isna(date):
            return "Unknown"
        try:
            return date.strftime('%b %Y')  # e.g., "Oct 2025"
        except:
            return str(date)
    
    def score_revenue_growth(self, metrics):
        """Score revenue growth trends"""
        if not metrics or not metrics.get('revenue') or not metrics.get('revenue_prev'):
            return 0, "Unable to assess revenue growth - insufficient data"
        
        try:
            revenue = float(metrics['revenue'])
            revenue_prev = float(metrics['revenue_prev'])
            latest_qtr = self.format_quarter_date(metrics['latest_quarter_date'])
            prev_qtr = self.format_quarter_date(metrics['prev_quarter_date'])
            
            growth = ((revenue - revenue_prev) / revenue_prev) * 100
            
            # Score based on growth rate
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
            
            # Format revenue in billions/millions
            rev_b = revenue / 1e9
            rev_prev_b = revenue_prev / 1e9
            
            reasoning = f"Revenue: ${rev_b:.2f}B ({latest_qtr}) vs ${rev_prev_b:.2f}B ({prev_qtr}) = {growth:+.1f}% QoQ ({status})"
            return score, reasoning
        except Exception as e:
            return 0, f"Unable to calculate revenue growth: {str(e)}"
    
    def score_profitability(self, metrics):
        """Score profitability metrics"""
        if not metrics:
            return 0, "Unable to assess profitability"
        
        try:
            net_income = metrics.get('net_income')
            net_income_prev = metrics.get('net_income_prev')
            latest_qtr = self.format_quarter_date(metrics['latest_quarter_date'])
            
            if not net_income or not net_income_prev:
                return 0, "Insufficient profitability data"
            
            net_income = float(net_income)
            net_income_prev = float(net_income_prev)
            
            # Check profitability
            if net_income <= 0:
                score = -2.0
                status = "UNPROFITABLE"
                reasoning = f"Net Income: ${net_income/1e9:.2f}B ({latest_qtr}) - UNPROFITABLE"
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
                
                ni_b = net_income / 1e9
                reasoning = f"Net Income: ${ni_b:.2f}B ({latest_qtr}), Growth: {profit_growth:+.1f}% QoQ ({status})"
            
            return score, reasoning
        except Exception as e:
            return 0, f"Unable to calculate profitability: {str(e)}"
    
    def score_margins(self, metrics):
        """Score profit margins"""
        if not metrics:
            return 0, "Unable to assess margins"
        
        try:
            profit_margin = metrics.get('profit_margin')
            
            if not profit_margin:
                # Calculate manually if not available
                if metrics.get('net_income') and metrics.get('revenue'):
                    profit_margin = float(metrics['net_income']) / float(metrics['revenue'])
                else:
                    return 0, "Margin data unavailable"
            
            profit_margin_pct = float(profit_margin) * 100
            
            if profit_margin_pct > 20:
                score = 2.0
                status = "EXCELLENT"
            elif profit_margin_pct > 15:
                score = 1.5
                status = "STRONG"
            elif profit_margin_pct > 10:
                score = 1.0
                status = "GOOD"
            elif profit_margin_pct > 5:
                score = 0.5
                status = "AVERAGE"
            elif profit_margin_pct > 0:
                score = 0
                status = "LOW"
            else:
                score = -2.0
                status = "NEGATIVE"
            
            reasoning = f"Net Profit Margin: {profit_margin_pct:.1f}% ({status})"
            return score, reasoning
        except Exception as e:
            return 0, f"Unable to calculate margins: {str(e)}"
    
    def score_financial_health(self, metrics):
        """Score overall financial health"""
        if not metrics:
            return 0, "Unable to assess financial health"
        
        score = 0
        factors = []
        
        try:
            # Current ratio (liquidity)
            current_ratio = metrics.get('current_ratio')
            if current_ratio and not pd.isna(current_ratio):
                if current_ratio > 2.0:
                    score += 0.5
                    factors.append(f"Strong liquidity (CR: {current_ratio:.2f})")
                elif current_ratio < 1.0:
                    score -= 0.5
                    factors.append(f"Weak liquidity (CR: {current_ratio:.2f})")
                else:
                    factors.append(f"Adequate liquidity (CR: {current_ratio:.2f})")
            
            # Debt to equity
            debt_to_equity = metrics.get('debt_to_equity')
            if debt_to_equity and not pd.isna(debt_to_equity):
                if debt_to_equity < 0.5:
                    score += 0.5
                    factors.append(f"Low debt (D/E: {debt_to_equity:.2f})")
                elif debt_to_equity > 2.0:
                    score -= 0.5
                    factors.append(f"High debt (D/E: {debt_to_equity:.2f})")
            
            # ROE
            roe = metrics.get('roe')
            if roe and not pd.isna(roe):
                roe_pct = roe * 100
                if roe > 0.20:
                    score += 1.0
                    factors.append(f"Excellent ROE ({roe_pct:.1f}%)")
                elif roe > 0.15:
                    score += 0.5
                    factors.append(f"Good ROE ({roe_pct:.1f}%)")
                elif roe < 0.05:
                    score -= 0.5
                    factors.append(f"Weak ROE ({roe_pct:.1f}%)")
            
            # Free Cash Flow
            fcf = metrics.get('free_cash_flow')
            if fcf and not pd.isna(fcf):
                if fcf > 0:
                    score += 0.5
                    fcf_b = fcf / 1e9
                    factors.append(f"Positive FCF (${fcf_b:.2f}B)")
                else:
                    score -= 0.5
                    factors.append("Negative FCF")
            
            score = max(-2.0, min(2.0, score))
            reasoning = "Financial health: " + ", ".join(factors) if factors else "Limited data available"
            
            return score, reasoning
        except Exception as e:
            return 0, f"Unable to assess financial health: {str(e)}"
    
    def score_guidance(self, metrics):
        """Score based on forward guidance"""
        if not metrics:
            return 0, "Unable to assess guidance"
        
        try:
            forward_eps = metrics.get('forward_eps')
            trailing_eps = metrics.get('trailing_eps')
            
            if not forward_eps or not trailing_eps or pd.isna(forward_eps) or pd.isna(trailing_eps):
                return 0, "Forward guidance data unavailable"
            
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
            
            reasoning = f"Forward EPS: ${forward_eps:.2f} vs Trailing: ${trailing_eps:.2f} = {eps_growth:+.1f}% growth ({status})"
            return score, reasoning
        except Exception as e:
            return 0, f"Unable to assess guidance: {str(e)}"
    
    def analyze(self, ticker: str, verbose: bool = True):
        """Perform complete company analysis with LATEST data"""
        if verbose:
            print(f"\n{'='*80}")
            print(f"COMPANY PERFORMANCE ANALYSIS: {ticker.upper()}")
            print(f"Analysis Date: {self.current_date.strftime('%Y-%m-%d')}")
            print(f"{'='*80}\n")
        
        # Get financial metrics
        metrics = self.extract_financial_metrics(ticker)
        
        if not metrics:
            return {
                'success': False,
                'error': 'Unable to fetch financial data',
                'ticker': ticker.upper()
            }
        
        # Check data freshness
        if metrics.get('is_stale'):
            warning = f"⚠️ WARNING: Data is {metrics['data_age_days']} days old (last quarter: {self.format_quarter_date(metrics['latest_quarter_date'])})"
            if verbose:
                print(warning + "\n")
        else:
            if verbose:
                print(f"✅ Data is fresh - Latest quarter: {self.format_quarter_date(metrics['latest_quarter_date'])} ({metrics['data_age_days']} days old)\n")
        
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
            confidence = "High"
        elif composite >= 6.5:
            signal = "BUY"
            confidence = "Medium-High"
        elif composite >= 5.5:
            signal = "HOLD (Lean Buy)"
            confidence = "Medium"
        elif composite >= 4.5:
            signal = "HOLD"
            confidence = "Medium"
        elif composite >= 3.5:
            signal = "HOLD (Lean Sell)"
            confidence = "Medium"
        elif composite >= 2.5:
            signal = "SELL"
            confidence = "Medium-High"
        else:
            signal = "STRONG SELL"
            confidence = "High"
        
        # Adjust confidence if data is stale
        if metrics.get('is_stale'):
            confidence = "Low (Stale Data)"
        
        if verbose:
            print(f"{'='*80}")
            print(f"COMPANY SCORE: {composite}/10")
            print(f"RECOMMENDATION: {signal}")
            print(f"CONFIDENCE: {confidence}")
            print(f"{'='*80}\n")
        
        return {
            'success': True,
            'ticker': ticker.upper(),
            'score': composite,
            'signal': signal,
            'confidence': confidence,
            'data_date': self.format_quarter_date(metrics['latest_quarter_date']),
            'data_age_days': metrics['data_age_days'],
            'is_stale': metrics.get('is_stale', False),
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
    print(f"Data from: {result['data_date']} ({result['data_age_days']} days old)")
