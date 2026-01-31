"""
Customer Analysis Module - Module 3
Identifies and analyzes customer relationships for demand-side risk assessment
"""

from edgar import Company, set_identity
import anthropic
import os
import yfinance as yf
from datetime import datetime
from typing import Dict, List, Optional
import json
import re

# CHANGE THIS TO YOUR EMAIL
set_identity("Paul Balasubramanian pb2963@columbia.edu")


class CustomerAnalyzer:
    """Analyzes customer relationships and demand-side risks"""
    
    def __init__(self, anthropic_api_key: Optional[str] = None):
        """Initialize with Anthropic API key"""
        self.api_key = anthropic_api_key or os.environ.get('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("Anthropic API key required")
        
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.current_date = datetime.now()
        self.total_tokens = 0
    
    def identify_customers_with_web_search(self, ticker: str, company_name: str) -> Dict:
        """Use Claude with web search to identify top 5 customers"""
        
        prompt = f"""Search the web to identify the TOP 5 most important customers for {company_name} ({ticker}).

Find customers by searching for:
- "{company_name} top customers 2025"
- "{company_name} largest buyers"
- "{company_name} revenue by customer"
- "{company_name} customer concentration"

For each customer found, provide:
1. Customer name (full company name)
2. Stock ticker if publicly traded, otherwise "PRIVATE"
3. What they buy (specific products/services)
4. Importance level: Critical, High, or Medium based on:
   - Revenue contribution (% of total revenue)
   - Strategic importance
   - Contract size
5. Revenue contribution ($ or % if mentioned in sources)
6. Recent developments (CapEx changes, contract renewals, expansions)
7. CapEx trends (are they increasing or decreasing spending?)

Focus on:
- Publicly traded customers (need their financial data)
- Recent customer news (2024-2025)
- CapEx and investment trends
- Contract renewals or cancellations

Return your findings in this EXACT JSON format with NO other text:
{{
  "customers": [
    {{
      "name": "Customer Company Name",
      "ticker": "TICK or PRIVATE",
      "purchases": "What they buy",
      "importance": "Critical|High|Medium",
      "revenue_contribution": "X% or $Y description",
      "recent_developments": "Recent news about relationship",
      "capex_trend": "Increasing|Stable|Decreasing",
      "source_summary": "Where info came from"
    }}
  ],
  "overall_customer_concentration": "High|Medium|Low",
  "key_findings": ["Finding 1", "Finding 2", "Finding 3"],
  "search_quality": "High|Medium|Low"
}}

CRITICAL: Return ONLY valid JSON. No explanatory text."""
        
        try:
            # Call Claude with web search
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                temperature=0,
                tools=[{
                    "type": "web_search_20250305",
                    "name": "web_search"
                }],
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            self.total_tokens += message.usage.input_tokens + message.usage.output_tokens
            
            # Extract text
            response_text = ""
            for block in message.content:
                if block.type == "text":
                    response_text += block.text
            
            if not response_text or len(response_text.strip()) == 0:
                return {
                    'success': False,
                    'error': 'Empty response from Claude',
                    'customers': []
                }
            
            # Clean response
            response_text = response_text.strip()
            
            # Remove markdown
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]
            
            # Extract JSON
            start = response_text.find('{')
            end = response_text.rfind('}')
            
            if start == -1 or end == -1:
                return {
                    'success': False,
                    'error': f'No JSON found in response',
                    'customers': []
                }
            
            response_text = response_text[start:end+1]
            
            # Parse JSON
            try:
                result = json.loads(response_text)
            except json.JSONDecodeError as e:
                return {
                    'success': False,
                    'error': f'JSON parse error: {str(e)}',
                    'customers': []
                }
            
            customers = result.get('customers', [])
            if not isinstance(customers, list):
                customers = []
            
            return {
                'success': True,
                'customers': customers[:5],
                'overall_concentration': result.get('overall_customer_concentration', 'Medium'),
                'key_findings': result.get('key_findings', []),
                'search_quality': result.get('search_quality', 'Medium')
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Web search failed: {str(e)}",
                'customers': []
            }
    
    def get_customer_financials(self, ticker: str) -> Optional[Dict]:
        """Get financial metrics and CapEx trends for customer"""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Get quarterly financials
            income = stock.quarterly_financials
            cashflow = stock.quarterly_cashflow
            
            if income.empty:
                return {
                    'ticker': ticker,
                    'market_cap': info.get('marketCap'),
                    'revenue': None
                }
            
            # Revenue trends
            latest_quarter = income.columns[0]
            prev_quarter = income.columns[1] if len(income.columns) > 1 else None
            
            revenue = income.loc['Total Revenue'].iloc[0] if 'Total Revenue' in income.index else None
            revenue_prev = income.loc['Total Revenue'].iloc[1] if 'Total Revenue' in income.index and prev_quarter is not None else None
            
            revenue_growth = None
            if revenue and revenue_prev:
                revenue_growth = ((revenue - revenue_prev) / revenue_prev) * 100
            
            # CapEx analysis
            capex = None
            capex_prev = None
            capex_growth = None
            
            if not cashflow.empty and 'Capital Expenditure' in cashflow.index:
                capex = abs(cashflow.loc['Capital Expenditure'].iloc[0])
                if len(cashflow.columns) > 1:
                    capex_prev = abs(cashflow.loc['Capital Expenditure'].iloc[1])
                    if capex and capex_prev:
                        capex_growth = ((capex - capex_prev) / capex_prev) * 100
            
            return {
                'ticker': ticker,
                'company_name': info.get('longName', ticker),
                'market_cap': info.get('marketCap'),
                'revenue': revenue,
                'revenue_growth': revenue_growth,
                'capex': capex,
                'capex_growth': capex_growth,
                'profit_margin': info.get('profitMargins'),
                'free_cash_flow': info.get('freeCashflow'),
                'latest_quarter': latest_quarter
            }
            
        except Exception as e:
            return None
    
    def get_customer_10k(self, ticker: str) -> Optional[Dict]:
        """Fetch customer's latest 10-K for strategic insights"""
        try:
            company = Company(ticker)
            
            filing = None
            try:
                filings = company.get_filings(form="10-K")
                for f in filings:
                    filing = f
                    break
            except:
                pass
            
            if not filing:
                return None
            
            # Get text
            try:
                full_text = filing.text()
            except:
                try:
                    full_text = str(filing.html())
                    full_text = re.sub('<[^<]+?>', ' ', full_text)
                except:
                    return None
            
            if not full_text or len(full_text) < 5000:
                return None
            
            # Extract MD&A for investment plans
            mda_pattern = r"(?:ITEM\s+7|Item\s+7).*?(?:ITEM\s+[78]|Item\s+[78]|$)"
            mda_match = re.search(mda_pattern, full_text, re.DOTALL | re.IGNORECASE)
            
            mda_text = ""
            if mda_match:
                mda_text = full_text[mda_match.start():mda_match.start()+30000]
            
            return {
                'success': True,
                'company_name': company.name,
                'filing_date': str(filing.filing_date),
                'mda_text': mda_text[:30000]
            }
            
        except Exception as e:
            return None
    
    def analyze_customer_demand(self, customer: Dict, customer_10k: Dict,
                                financials: Dict, target_company: str) -> Dict:
        """Use Claude to analyze customer's demand outlook"""
        
        customer_name = customer['name']
        purchases = customer.get('purchases', 'Unknown')
        
        # Build financial context
        financial_context = ""
        if financials:
            mc = financials.get('market_cap', 0)
            rev = financials.get('revenue', 0)
            rev_growth = financials.get('revenue_growth', 0)
            capex = financials.get('capex', 0)
            capex_growth = financials.get('capex_growth', 0)
            
            if mc:
                financial_context += f"Market Cap: ${mc/1e9:.1f}B\n"
            if rev:
                financial_context += f"Revenue (Q): ${rev/1e9:.1f}B\n"
            if rev_growth:
                financial_context += f"Revenue Growth: {rev_growth:+.1f}% QoQ\n"
            if capex:
                financial_context += f"CapEx (Q): ${capex/1e9:.2f}B\n"
            if capex_growth:
                financial_context += f"CapEx Growth: {capex_growth:+.1f}% QoQ\n"
        
        filing_context = ""
        if customer_10k:
            filing_context = f"10-K filed: {customer_10k['filing_date']}\n\nMD&A excerpt:\n{customer_10k['mda_text'][:15000]}"
        
        prompt = f"""Analyze {customer_name}'s demand outlook for {target_company}.

CUSTOMER CONTEXT:
- What they buy: {purchases}
- Importance: {customer.get('importance', 'Unknown')}
- Revenue contribution: {customer.get('revenue_contribution', 'Not disclosed')}
- Recent developments: {customer.get('recent_developments', 'None')}
- CapEx trend: {customer.get('capex_trend', 'Unknown')}

FINANCIAL METRICS:
{financial_context if financial_context else "Limited data"}

10-K ANALYSIS:
{filing_context if filing_context else "Not available"}

Provide analysis focusing on DEMAND-SIDE RISK:

DEMAND ASSESSMENT:
1. Growth Trajectory: Is this customer growing or declining?
2. CapEx Momentum: Are they increasing investment in areas that use {target_company}'s products?
3. Strategic Priority: How important is {target_company}'s product to their strategy?
4. Budget Health: Can they afford to maintain/increase spending?

RISK FACTORS:
1. Concentration Risk: How dependent is {target_company} on this customer?
2. Competition Risk: Are they exploring alternatives?
3. Budget Cuts: Any risk of CapEx reduction?
4. Contract Risk: Renewal timing, pricing pressure

DEMAND OUTLOOK:
- Increasing (strong growth expected)
- Stable (maintain current levels)
- Declining (reduction expected)

Return JSON:
{{
  "demand_assessment": {{
    "growth_trajectory": "Growing|Stable|Declining",
    "capex_momentum": "Accelerating|Stable|Decelerating",
    "strategic_priority": "Critical|High|Medium|Low",
    "budget_health": "Strong|Adequate|Constrained"
  }},
  "risk_factors": {{
    "concentration_risk": "High|Medium|Low",
    "competition_risk": "High|Medium|Low",
    "budget_risk": "High|Medium|Low",
    "contract_risk": "High|Medium|Low"
  }},
  "demand_outlook": "Increasing|Stable|Declining",
  "opportunities": ["Opportunity 1", "Opportunity 2"],
  "risks": ["Risk 1", "Risk 2"],
  "demand_score": 7.5,
  "summary": "2-3 sentence assessment"
}}

Return ONLY valid JSON."""
        
        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2500,
                temperature=0,
                messages=[{"role": "user", "content": prompt}]
            )
            
            self.total_tokens += message.usage.input_tokens + message.usage.output_tokens
            
            response = message.content[0].text.strip()
            
            # Clean JSON
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
            
            start = response.find('{')
            end = response.rfind('}')
            if start != -1 and end != -1:
                response = response[start:end+1]
            
            result = json.loads(response)
            
            return {
                'success': True,
                **result
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def score_customer(self, customer: Dict, demand_analysis: Dict,
                      financials: Optional[Dict]) -> float:
        """Calculate customer score (-2 to +2, higher = better demand outlook)"""
        
        score = 0.0
        
        # Factor 1: Importance (high concentration is RISK)
        importance = customer.get('importance', 'Medium')
        if importance == 'Critical':
            score -= 1.0  # Concentration risk
        elif importance == 'High':
            score -= 0.5
        else:
            score += 0.5  # Diversification good
        
        # Factor 2: Demand outlook
        if demand_analysis.get('success'):
            outlook = demand_analysis.get('demand_outlook', 'Stable')
            if outlook == 'Increasing':
                score += 1.5
            elif outlook == 'Declining':
                score -= 1.5
        
        # Factor 3: CapEx momentum
        if financials:
            capex_growth = financials.get('capex_growth')
            if capex_growth:
                if capex_growth > 20:
                    score += 1.0
                elif capex_growth > 10:
                    score += 0.5
                elif capex_growth < -10:
                    score -= 0.5
                elif capex_growth < -20:
                    score -= 1.0
        
        # Factor 4: Financial health
        if financials:
            rev_growth = financials.get('revenue_growth')
            if rev_growth:
                if rev_growth > 15:
                    score += 0.5
                elif rev_growth < -5:
                    score -= 0.5
        
        # Factor 5: Demand score from analysis
        if demand_analysis.get('success'):
            demand_score = demand_analysis.get('demand_score', 5.0)
            score += (demand_score - 5) / 5  # Normalize
        
        return max(-2.0, min(2.0, score))
    
    def analyze(self, ticker: str, verbose: bool = True) -> Dict:
        """Complete customer analysis"""
        
        if verbose:
            print(f"\n{'='*80}")
            print(f"CUSTOMER ANALYSIS: {ticker.upper()}")
            print(f"{'='*80}\n")
            print("Step 1: Searching web to identify customers...")
        
        # Get company name
        try:
            company = Company(ticker)
            company_name = company.name
        except:
            company_name = ticker.upper()
        
        # Step 1: Web search for customers
        customer_search = self.identify_customers_with_web_search(ticker, company_name)
        
        if not customer_search.get('success'):
            return {
                'success': False,
                'error': customer_search.get('error', 'Failed to identify customers'),
                'ticker': ticker.upper()
            }
        
        customers = customer_search.get('customers', [])
        
        if not customers or len(customers) == 0:
            return {
                'success': False,
                'error': 'No customers identified',
                'ticker': ticker.upper()
            }
        
        if verbose:
            print(f"✅ Found {len(customers)} major customers\n")
            print("Step 2: Analyzing each customer...\n")
        
        # Step 2: Analyze each customer
        analyzed_customers = []
        
        for i, customer in enumerate(customers[:5]):
            if verbose:
                print(f"  [{i+1}/5] {customer['name']}...")
            
            customer_result = customer.copy()
            
            if customer.get('ticker') != 'PRIVATE' and customer.get('ticker'):
                ticker_sym = customer['ticker']
                
                # Get financials (including CapEx)
                financials = self.get_customer_financials(ticker_sym)
                customer_result['financials'] = financials
                
                # Get 10-K
                customer_10k = self.get_customer_10k(ticker_sym)
                customer_result['has_10k'] = bool(customer_10k)
                
                # Analyze demand
                demand = self.analyze_customer_demand(
                    customer, customer_10k, financials, company_name
                )
                customer_result['demand_analysis'] = demand
                
                # Score
                score = self.score_customer(customer, demand, financials)
                customer_result['score'] = score
                
                if verbose:
                    status = "✅" if score > 0 else "⚠️" if score > -0.5 else "❌"
                    print(f"     {status} Score: {score:+.1f}/2.0")
            else:
                customer_result['financials'] = None
                customer_result['has_10k'] = False
                customer_result['demand_analysis'] = {
                    'success': False,
                    'error': 'Private company'
                }
                customer_result['score'] = 0.0
                
                if verbose:
                    print(f"     🔒 Private company")
            
            analyzed_customers.append(customer_result)
        
        # Calculate aggregate score
        scores = [c.get('score', 0) for c in analyzed_customers]
        avg_score = sum(scores) / len(scores) if scores else 0
        composite = round(5.5 + (avg_score * 2.25), 1)
        
        # Determine signal
        if composite >= 7.5:
            signal = "STRONG DEMAND"
        elif composite >= 6.5:
            signal = "GROWING DEMAND"
        elif composite >= 5.5:
            signal = "STABLE DEMAND"
        elif composite >= 4.5:
            signal = "WEAKENING DEMAND"
        else:
            signal = "DECLINING DEMAND"
        
        if verbose:
            print(f"\n{'='*80}")
            print(f"CUSTOMER DEMAND SCORE: {composite}/10")
            print(f"DEMAND OUTLOOK: {signal}")
            print(f"{'='*80}")
            print(f"Cost: ${self.total_tokens * 0.003 / 1000:.3f}")
            print(f"{'='*80}\n")
        
        return {
            'success': True,
            'ticker': ticker.upper(),
            'company_name': company_name,
            'score': composite,
            'signal': signal,
            'confidence': 'High' if customer_search.get('search_quality') == 'High' else 'Medium',
            'overall_concentration': customer_search.get('overall_concentration', 'Medium'),
            'key_findings': customer_search.get('key_findings', []),
            'customers': analyzed_customers,
            'search_quality': customer_search.get('search_quality', 'Medium'),
            'tokens_used': self.total_tokens,
            'estimated_cost': self.total_tokens * 0.003 / 1000
        }
