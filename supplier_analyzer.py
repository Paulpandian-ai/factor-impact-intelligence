"""
Enhanced Supplier Analysis Module - ROBUST VERSION
Handles web search responses more carefully
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


class SupplierAnalyzer:
    """Enhanced supplier analysis using web search + 10-K analysis"""
    
    def __init__(self, anthropic_api_key: Optional[str] = None):
        """Initialize with Anthropic API key"""
        self.api_key = anthropic_api_key or os.environ.get('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("Anthropic API key required")
        
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.current_date = datetime.now()
        self.total_tokens = 0
    
    def identify_suppliers_with_web_search(self, ticker: str, company_name: str) -> Dict:
        """Use Claude with web search to identify top 5 suppliers"""
        
        prompt = f"""Search the web to identify the TOP 5 most critical suppliers for {company_name} ({ticker}).

Find suppliers by searching for:
- "{company_name} suppliers 2025"
- "{company_name} supply chain"
- "{company_name} manufacturing partners"

For each supplier found, provide:
1. Supplier name (full company name)
2. Stock ticker if publicly traded, otherwise "PRIVATE"
3. What they supply (specific components/services)
4. Importance level: Critical, High, or Medium
5. Financial exposure ($ or % if mentioned in sources)
6. Recent news about the relationship

Focus on:
- Publicly traded suppliers (need 10-K access)
- Manufacturing partners, foundries, component suppliers
- Recent supply chain news (2024-2025)

Return your findings in this EXACT JSON format with NO other text before or after:
{{
  "suppliers": [
    {{
      "name": "Supplier Company Name",
      "ticker": "TICK or PRIVATE",
      "supplies": "What they provide",
      "importance": "Critical|High|Medium",
      "financial_exposure": "Description",
      "recent_context": "Recent news",
      "source_summary": "Source info"
    }}
  ],
  "overall_risk_assessment": "High|Medium|Low",
  "key_findings": ["Finding 1", "Finding 2", "Finding 3"],
  "search_quality": "High|Medium|Low"
}}

CRITICAL: Return ONLY valid JSON. No explanatory text before or after."""
        
        try:
            # Call Claude with web search tool
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
            
            # Track tokens
            self.total_tokens += message.usage.input_tokens + message.usage.output_tokens
            
            # Extract ALL text from response blocks
            response_text = ""
            for block in message.content:
                if block.type == "text":
                    response_text += block.text
            
            if not response_text or len(response_text.strip()) == 0:
                return {
                    'success': False,
                    'error': 'Empty response from Claude',
                    'suppliers': []
                }
            
            # Aggressively clean the response
            response_text = response_text.strip()
            
            # Remove markdown code blocks
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]
            
            # Remove any leading/trailing text that's not JSON
            # Find the first { and last }
            start = response_text.find('{')
            end = response_text.rfind('}')
            
            if start == -1 or end == -1:
                return {
                    'success': False,
                    'error': f'No JSON found in response: {response_text[:200]}',
                    'suppliers': []
                }
            
            response_text = response_text[start:end+1]
            
            # Try to parse JSON
            try:
                result = json.loads(response_text)
            except json.JSONDecodeError as e:
                return {
                    'success': False,
                    'error': f'JSON parse error: {str(e)}. Response: {response_text[:200]}',
                    'suppliers': []
                }
            
            # Validate structure
            if not isinstance(result, dict):
                return {
                    'success': False,
                    'error': 'Response is not a JSON object',
                    'suppliers': []
                }
            
            suppliers = result.get('suppliers', [])
            if not isinstance(suppliers, list):
                suppliers = []
            
            return {
                'success': True,
                'suppliers': suppliers[:5],
                'overall_risk': result.get('overall_risk_assessment', 'Medium'),
                'key_findings': result.get('key_findings', []),
                'search_quality': result.get('search_quality', 'Medium')
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Web search failed: {str(e)}",
                'suppliers': []
            }
    
    def get_supplier_10k(self, ticker: str) -> Optional[Dict]:
        """Fetch supplier's latest 10-K filing"""
        try:
            company = Company(ticker)
            
            # Get latest 10-K
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
                    # Clean HTML
                    full_text = re.sub('<[^<]+?>', ' ', full_text)
                except:
                    return None
            
            if not full_text or len(full_text) < 5000:
                return None
            
            # Extract MD&A and Risk sections (simplified)
            mda_pattern = r"(?:ITEM\s+7|Item\s+7).*?(?:ITEM\s+[78]|Item\s+[78]|$)"
            risk_pattern = r"(?:ITEM\s+1A|Item\s+1A).*?(?:ITEM\s+[12B]|Item\s+[12B]|$)"
            
            mda_match = re.search(mda_pattern, full_text, re.DOTALL | re.IGNORECASE)
            risk_match = re.search(risk_pattern, full_text, re.DOTALL | re.IGNORECASE)
            
            mda_text = full_text[mda_match.start():mda_match.start()+25000] if mda_match else ""
            risk_text = full_text[risk_match.start():risk_match.start()+20000] if risk_match else ""
            
            key_text = mda_text + "\n\n" + risk_text
            
            return {
                'success': True,
                'company_name': company.name,
                'filing_date': str(filing.filing_date),
                'key_text': key_text[:45000]
            }
            
        except Exception as e:
            return None
    
    def get_supplier_financials(self, ticker: str) -> Optional[Dict]:
        """Get key financial metrics for supplier"""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            income = stock.quarterly_financials
            
            if income.empty:
                return {
                    'ticker': ticker,
                    'market_cap': info.get('marketCap'),
                    'revenue': None,
                    'margin': info.get('profitMargins')
                }
            
            latest_quarter = income.columns[0]
            prev_quarter = income.columns[1] if len(income.columns) > 1 else None
            
            revenue = income.loc['Total Revenue'].iloc[0] if 'Total Revenue' in income.index else None
            revenue_prev = income.loc['Total Revenue'].iloc[1] if 'Total Revenue' in income.index and prev_quarter is not None else None
            net_income = income.loc['Net Income'].iloc[0] if 'Net Income' in income.index else None
            
            revenue_growth = None
            if revenue and revenue_prev:
                revenue_growth = ((revenue - revenue_prev) / revenue_prev) * 100
            
            return {
                'ticker': ticker,
                'company_name': info.get('longName', ticker),
                'market_cap': info.get('marketCap'),
                'revenue': revenue,
                'revenue_growth': revenue_growth,
                'net_income': net_income,
                'profit_margin': info.get('profitMargins'),
                'debt_to_equity': info.get('debtToEquity'),
                'current_ratio': info.get('currentRatio'),
                'latest_quarter': latest_quarter
            }
            
        except Exception as e:
            return None
    
    def analyze_supplier_impact(self, supplier: Dict, supplier_10k: Dict, 
                                financials: Dict, target_company: str) -> Dict:
        """Use Claude to analyze supplier's impact"""
        
        supplier_name = supplier['name']
        supplies = supplier.get('supplies', 'Unknown')
        
        financial_context = ""
        if financials:
            mc = financials.get('market_cap', 0)
            rev = financials.get('revenue', 0)
            margin = financials.get('profit_margin', 0)
            growth = financials.get('revenue_growth', 0)
            
            if mc:
                financial_context += f"Market Cap: ${mc/1e9:.1f}B\n"
            if rev:
                financial_context += f"Revenue (latest quarter): ${rev/1e9:.1f}B\n"
            if growth:
                financial_context += f"Revenue Growth: {growth:+.1f}% QoQ\n"
            if margin:
                financial_context += f"Profit Margin: {margin*100:.1f}%\n"
        
        filing_context = ""
        if supplier_10k:
            filing_context = f"10-K filed: {supplier_10k['filing_date']}\n\nKey excerpts:\n{supplier_10k['key_text'][:15000]}"
        
        prompt = f"""Analyze {supplier_name}'s impact on {target_company}.

SUPPLIER CONTEXT:
- What they supply: {supplies}
- Importance: {supplier.get('importance', 'Unknown')}
- Exposure: {supplier.get('financial_exposure', 'Not disclosed')}

FINANCIALS:
{financial_context if financial_context else "Limited data"}

10-K ANALYSIS:
{filing_context if filing_context else "Not available"}

Provide comprehensive analysis in this EXACT JSON format with NO other text:
{{
  "quantitative": {{
    "financial_scale": "Assessment text",
    "capacity_assessment": "Assessment text",
    "investment_outlook": "Assessment text",
    "mutual_dependency": "Assessment text"
  }},
  "qualitative": {{
    "strategic_importance": "Assessment text",
    "relationship_strength": "Assessment text",
    "risk_level": "High|Medium|Low",
    "alternative_availability": "Assessment text"
  }},
  "opportunities": ["Opportunity 1", "Opportunity 2"],
  "challenges": ["Challenge 1", "Challenge 2"],
  "risks": ["Risk 1", "Risk 2"],
  "reliability_score": 7.5,
  "summary": "2-3 sentence summary"
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
            
            # Extract JSON
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
    
    def score_supplier(self, supplier: Dict, impact_analysis: Dict, 
                      financials: Optional[Dict]) -> float:
        """Calculate supplier risk score (-2 to +2)"""
        
        score = 0.0
        
        # Factor 1: Importance
        importance = supplier.get('importance', 'Medium')
        if importance == 'Critical':
            score -= 1.0
        elif importance == 'High':
            score -= 0.5
        else:
            score += 0.5
        
        # Factor 2: Reliability
        if impact_analysis.get('success'):
            reliability = impact_analysis.get('reliability_score', 5.0)
            score += (reliability - 5) / 5
        
        # Factor 3: Financial health
        if financials:
            margin = financials.get('profit_margin')
            growth = financials.get('revenue_growth')
            
            if margin and margin > 0.15:
                score += 0.5
            elif margin and margin < 0.05:
                score -= 0.5
            
            if growth and growth > 10:
                score += 0.3
            elif growth and growth < -5:
                score -= 0.3
        
        # Factor 4: Risk level
        if impact_analysis.get('success'):
            risk_level = impact_analysis.get('qualitative', {}).get('risk_level', 'Medium')
            if risk_level == 'Low':
                score += 0.5
            elif risk_level == 'High':
                score -= 0.5
        
        return max(-2.0, min(2.0, score))
    
    def analyze(self, ticker: str, verbose: bool = True) -> Dict:
        """Complete enhanced supplier analysis"""
        
        if verbose:
            print(f"\n{'='*80}")
            print(f"ENHANCED SUPPLIER ANALYSIS: {ticker.upper()}")
            print(f"{'='*80}\n")
            print("Step 1: Searching web to identify suppliers...")
        
        # Get company name
        try:
            company = Company(ticker)
            company_name = company.name
        except:
            company_name = ticker.upper()
        
        # Step 1: Web search for suppliers
        supplier_search = self.identify_suppliers_with_web_search(ticker, company_name)
        
        if not supplier_search.get('success'):
            return {
                'success': False,
                'error': supplier_search.get('error', 'Failed to identify suppliers'),
                'ticker': ticker.upper()
            }
        
        suppliers = supplier_search.get('suppliers', [])
        
        if not suppliers or len(suppliers) == 0:
            return {
                'success': False,
                'error': 'No suppliers identified from web search',
                'ticker': ticker.upper()
            }
        
        if verbose:
            print(f"✅ Found {len(suppliers)} suppliers\n")
            print("Step 2: Analyzing each supplier...\n")
        
        # Step 2: Analyze each supplier
        analyzed_suppliers = []
        
        for i, supplier in enumerate(suppliers[:5]):
            if verbose:
                print(f"  [{i+1}/5] {supplier['name']}...")
            
            supplier_result = supplier.copy()
            
            if supplier.get('ticker') != 'PRIVATE' and supplier.get('ticker'):
                ticker_sym = supplier['ticker']
                
                # Get 10-K
                supplier_10k = self.get_supplier_10k(ticker_sym)
                supplier_result['has_10k'] = bool(supplier_10k)
                
                # Get financials
                financials = self.get_supplier_financials(ticker_sym)
                supplier_result['financials'] = financials
                
                # Analyze impact
                impact = self.analyze_supplier_impact(
                    supplier, supplier_10k, financials, company_name
                )
                supplier_result['impact_analysis'] = impact
                
                # Score
                score = self.score_supplier(supplier, impact, financials)
                supplier_result['score'] = score
                
                if verbose:
                    status = "✅" if score > 0 else "⚠️" if score > -1 else "❌"
                    print(f"     {status} Score: {score:+.1f}/2.0")
            else:
                supplier_result['has_10k'] = False
                supplier_result['financials'] = None
                supplier_result['impact_analysis'] = {
                    'success': False,
                    'error': 'Private company'
                }
                supplier_result['score'] = -0.5
                
                if verbose:
                    print(f"     🔒 Private company")
            
            analyzed_suppliers.append(supplier_result)
        
        # Calculate aggregate score
        scores = [s.get('score', 0) for s in analyzed_suppliers]
        avg_score = sum(scores) / len(scores) if scores else 0
        composite = round(5.5 + (avg_score * 2.25), 1)
        
        if composite >= 7.0:
            signal = "LOW RISK"
        elif composite >= 5.5:
            signal = "MODERATE RISK"
        elif composite >= 4.0:
            signal = "ELEVATED RISK"
        else:
            signal = "HIGH RISK"
        
        if verbose:
            print(f"\n{'='*80}")
            print(f"RISK SCORE: {composite}/10")
            print(f"RISK LEVEL: {signal}")
            print(f"{'='*80}")
            print(f"Cost: ${self.total_tokens * 0.003 / 1000:.3f}")
            print(f"{'='*80}\n")
        
        return {
            'success': True,
            'ticker': ticker.upper(),
            'company_name': company_name,
            'score': composite,
            'signal': signal,
            'confidence': 'High' if supplier_search.get('search_quality') == 'High' else 'Medium',
            'overall_supplier_risk': supplier_search.get('overall_risk', 'Medium'),
            'key_findings': supplier_search.get('key_findings', []),
            'suppliers': analyzed_suppliers,
            'search_quality': supplier_search.get('search_quality', 'Medium'),
            'tokens_used': self.total_tokens,
            'estimated_cost': self.total_tokens * 0.003 / 1000
        }
