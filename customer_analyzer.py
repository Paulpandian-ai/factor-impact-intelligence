"""
Customer Analysis Module - WITH CACHING & RATE LIMIT HANDLING
Identifies and analyzes customer relationships with intelligent caching
"""

from edgar import Company, set_identity
import anthropic
import os
import yfinance as yf
from datetime import datetime
from typing import Dict, List, Optional
import json
import re
import time

# Import cache manager
try:
    from cache_manager import DataCacheManager
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False
    print("⚠️ cache_manager not found - running without caching")

# Set Edgar identity
set_identity("Paul Balasubramanian pb2963@columbia.edu")


class CustomerAnalyzer:
    """Analyzes customer relationships with caching and rate limit handling"""
    
    def __init__(self, anthropic_api_key: Optional[str] = None, use_cache: bool = True):
        """Initialize with Anthropic API key"""
        self.api_key = anthropic_api_key or os.environ.get('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("Anthropic API key required")
        
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.current_date = datetime.now()
        self.total_tokens = 0
        self.use_cache = use_cache and CACHE_AVAILABLE
        
        if self.use_cache:
            self.cache = DataCacheManager()
    
    def _rate_limit_delay(self, seconds: float = 2.0):
        """Add delay between API calls to avoid rate limits"""
        time.sleep(seconds)
    
    def identify_customers_with_web_search(self, ticker: str, company_name: str) -> Dict:
        """Use Claude with web search to identify top 5 customers - WITH CACHING"""
        
        # Check cache first (customers don't change often - cache for 7 days)
        if self.use_cache:
            cached = self.cache.get('customer_list', ticker=ticker)
            if cached:
                cached['_from_cache'] = True
                return cached
        
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
            # Rate limit protection
            self._rate_limit_delay(1.0)
            
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
            
            final_result = {
                'success': True,
                'customers': customers[:5],
                'overall_concentration': result.get('overall_customer_concentration', 'Medium'),
                'key_findings': result.get('key_findings', []),
                'search_quality': result.get('search_quality', 'Medium'),
                '_from_cache': False
            }
            
            # Cache the result
            if self.use_cache:
                self.cache.set('customer_list', final_result, ticker=ticker, cost=0.05)
            
            return final_result
            
        except anthropic.RateLimitError as e:
            return {
                'success': False,
                'error': f"Rate limit error: {str(e)}. Please wait 60 seconds and try again.",
                'customers': []
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Web search failed: {str(e)}",
                'customers': []
            }
    
    def get_customer_financials(self, ticker: str) -> Optional[Dict]:
        """Get financial metrics and CapEx trends for customer - WITH CACHING"""
        
        if self.use_cache:
            cached = self.cache.get('customer_financials', ticker=ticker)
            if cached:
                return cached
        
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
            
            result = {
                'ticker': ticker,
                'company_name': info.get('longName', ticker),
                'market_cap': info.get('marketCap'),
                'revenue': revenue,
                'revenue_growth': revenue_growth,
                'capex': capex,
                'capex_growth': capex_growth,
                'profit_margin': info.get('profitMargins'),
                'free_cash_flow': info.get('freeCashflow'),
                'latest_quarter': str(latest_quarter)
            }
            
            # Cache the result
            if self.use_cache:
                self.cache.set('customer_financials', result, ticker=ticker, cost=0.001)
            
            return result
            
        except Exception as e:
            return None
    
    def get_customer_10k(self, ticker: str) -> Optional[Dict]:
        """Fetch customer's latest 10-K filing - WITH CACHING"""
        
        if self.use_cache:
            cached = self.cache.get('sec_filing_text', ticker=ticker)
            if cached:
                return cached
        
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
            
            # Extract key sections
            mda_pattern = r"(?:ITEM\s+7|Item\s+7).*?(?:ITEM\s+[78]|Item\s+[78]|$)"
            mda_match = re.search(mda_pattern, full_text, re.DOTALL | re.IGNORECASE)
            mda_text = full_text[mda_match.start():mda_match.start()+25000] if mda_match else full_text[:25000]
            
            result = {
                'success': True,
                'company_name': company.name,
                'filing_date': str(filing.filing_date),
                'key_text': mda_text
            }
            
            if self.use_cache:
                self.cache.set('sec_filing_text', result, ticker=ticker, cost=0.01)
            
            return result
            
        except:
            return None
    
    def analyze_customer_demand(self, customer: Dict, customer_10k: Optional[Dict],
                               financials: Optional[Dict], target_company: str) -> Dict:
        """Analyze customer's demand outlook - WITH RATE LIMITING"""
        
        context_parts = []
        
        if customer_10k and customer_10k.get('key_text'):
            context_parts.append(f"10-K MD&A excerpts:\n{customer_10k['key_text'][:12000]}")
        
        if financials:
            context_parts.append(f"""
Financial metrics:
- Revenue: ${financials.get('revenue', 'N/A'):,.0f}
- Revenue Growth: {financials.get('revenue_growth', 'N/A'):.1f}%
- CapEx: ${financials.get('capex', 'N/A'):,.0f}
- CapEx Growth: {financials.get('capex_growth', 'N/A'):.1f}%
- Free Cash Flow: ${financials.get('free_cash_flow', 'N/A'):,.0f}
""")
        
        context = "\n".join(context_parts) if context_parts else "Limited data available"
        
        prompt = f"""Analyze the demand outlook for {customer['name']} ({customer.get('ticker', 'Unknown')}) 
as a customer of {target_company}.

They purchase: {customer.get('purchases', 'Unknown')}
Revenue contribution: {customer.get('revenue_contribution', 'Unknown')}
CapEx trend: {customer.get('capex_trend', 'Unknown')}

{context}

Return analysis as JSON:
{{
  "demand_outlook": "Increasing|Stable|Declining",
  "demand_score": 7.5,
  "capex_analysis": {{
    "trend": "Increasing|Stable|Decreasing",
    "implication": "What this means for {target_company}"
  }},
  "growth_drivers": ["Driver 1", "Driver 2"],
  "risk_factors": ["Risk 1", "Risk 2"],
  "contract_outlook": "Assessment of ongoing relationship",
  "strategic_importance": "High|Medium|Low",
  "summary": "2-3 sentence assessment"
}}

Return ONLY valid JSON."""
        
        try:
            # Rate limit protection
            self._rate_limit_delay(2.0)
            
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
            
        except anthropic.RateLimitError as e:
            return {
                'success': False,
                'error': f"Rate limit: {str(e)}"
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
        """Complete customer analysis with caching"""
        
        if verbose:
            print(f"\n{'='*80}")
            print(f"CUSTOMER ANALYSIS: {ticker.upper()}")
            if self.use_cache:
                print("Caching: ENABLED (7-day TTL for customer data)")
            print(f"{'='*80}\n")
            print("Step 1: Searching web to identify customers...")
        
        # Get company name
        try:
            company = Company(ticker)
            company_name = company.name
        except:
            company_name = ticker.upper()
        
        # Step 1: Web search for customers (cached)
        customer_search = self.identify_customers_with_web_search(ticker, company_name)
        
        if not customer_search.get('success'):
            return {
                'success': False,
                'error': customer_search.get('error', 'Failed to identify customers'),
                'ticker': ticker.upper()
            }
        
        if verbose and customer_search.get('_from_cache'):
            print("✅ Using cached customer list (fresh)")
        
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
                
                # Get financials (cached)
                financials = self.get_customer_financials(ticker_sym)
                customer_result['financials'] = financials
                
                # Get 10-K (cached)
                customer_10k = self.get_customer_10k(ticker_sym)
                customer_result['has_10k'] = bool(customer_10k)
                
                # Analyze demand (with rate limiting)
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
        composite = max(1, min(10, composite))
        
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
        
        estimated_cost = self.total_tokens * 0.003 / 1000
        
        if verbose:
            print(f"\n{'='*80}")
            print(f"CUSTOMER DEMAND SCORE: {composite}/10")
            print(f"DEMAND OUTLOOK: {signal}")
            print(f"{'='*80}")
            print(f"Cost: ${estimated_cost:.3f}")
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
            'estimated_cost': estimated_cost,
            '_from_cache': customer_search.get('_from_cache', False)
        }
