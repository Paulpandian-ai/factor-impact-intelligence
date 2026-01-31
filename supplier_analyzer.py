"""
Enhanced Supplier Analysis Module - Uses Web Search + 10-K Analysis
Identifies suppliers via web search, then analyzes their 10-Ks for impact
"""

from edgar import Company, set_identity
import anthropic
import os
import yfinance as yf
from datetime import datetime
from typing import Dict, List, Optional
import json

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
        
        prompt = f"""Search the web to identify the TOP 5 most critical suppliers for {company_name} ({ticker}) as of 2025-2026.

For each supplier, provide:
1. **Supplier Name** - Full company name
2. **Ticker Symbol** - Stock ticker if publicly traded (or "PRIVATE")
3. **What They Supply** - Specific products/services/components
4. **Importance Level** - Critical/High/Medium based on:
   - Revenue or cost dependency
   - Single-source vs multi-source
   - Strategic importance
5. **Financial Exposure** - $ amount or % of costs/revenue if available
6. **Recent Context** - Any recent news about the relationship

IMPORTANT:
- Focus on publicly traded suppliers (we need their 10-K filings)
- Prioritize manufacturers, foundries, component suppliers
- Look for recent supply chain news (2024-2025)
- Include revenue/cost exposure if mentioned in sources

Return ONLY valid JSON in this format:
{{
  "suppliers": [
    {{
      "name": "Supplier Company Name",
      "ticker": "TICK",
      "supplies": "What they provide",
      "importance": "Critical|High|Medium",
      "financial_exposure": "Description with $ or %",
      "recent_context": "Brief recent news",
      "source_summary": "Where info came from"
    }}
  ],
  "overall_risk_assessment": "High|Medium|Low",
  "key_findings": ["Finding 1", "Finding 2", "Finding 3"],
  "search_quality": "High|Medium|Low"
}}"""
        
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
            
            # Extract response (handle tool use)
            response_text = ""
            for block in message.content:
                if block.type == "text":
                    response_text += block.text
            
            # Clean JSON
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            # Parse JSON
            result = json.loads(response_text)
            
            return {
                'success': True,
                'suppliers': result.get('suppliers', [])[:5],
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
                    import re
                    full_text = re.sub('<[^<]+?>', ' ', full_text)
                except:
                    return None
            
            if not full_text or len(full_text) < 5000:
                return None
            
            # Extract key sections (MD&A and Risk Factors)
            # This is a simplified extraction - gets relevant portions
            mda_pattern = r"(?:ITEM\s+7|Item\s+7).*?(?:ITEM\s+[78]|Item\s+[78]|$)"
            risk_pattern = r"(?:ITEM\s+1A|Item\s+1A).*?(?:ITEM\s+[12B]|Item\s+[12B]|$)"
            
            import re
            mda_match = re.search(mda_pattern, full_text, re.DOTALL | re.IGNORECASE)
            risk_match = re.search(risk_pattern, full_text, re.DOTALL | re.IGNORECASE)
            
            mda_text = full_text[mda_match.start():mda_match.start()+25000] if mda_match else ""
            risk_text = full_text[risk_match.start():risk_match.start()+20000] if risk_match else ""
            
            # Combine key sections
            key_text = mda_text + "\n\n" + risk_text
            
            return {
                'success': True,
                'company_name': company.name,
                'filing_date': str(filing.filing_date),
                'key_text': key_text[:45000]  # Limit to 45K chars
            }
            
        except Exception as e:
            return None
    
    def get_supplier_financials(self, ticker: str) -> Optional[Dict]:
        """Get key financial metrics for supplier"""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Get quarterly financials
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
            
            # Calculate growth
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
        """Use Claude to analyze supplier's quantitative + qualitative impact"""
        
        supplier_name = supplier['name']
        supplies = supplier.get('supplies', 'Unknown')
        
        # Build context
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

FINANCIAL METRICS:
{financial_context if financial_context else "Limited financial data available"}

10-K FILING ANALYSIS:
{filing_context if filing_context else "10-K not available"}

Provide comprehensive analysis:

QUANTITATIVE IMPACT:
1. Financial Scale: Revenue size, growth rate, profitability
2. Capacity: Can they meet {target_company}'s demand? Any constraints?
3. Investment: CapEx plans, capacity expansion
4. Dependency: How important is {target_company} to this supplier?

QUALITATIVE IMPACT:
1. Strategic Importance: Technology leadership, market position
2. Relationship Strength: Long-term contracts, strategic partnership
3. Risk Assessment: Geographic, operational, financial, technology risks
4. Alternatives: How easily could {target_company} switch suppliers?

OPPORTUNITIES:
- What strengths does this supplier bring?
- Growth potential, innovation capability

CHALLENGES:
- What weaknesses or constraints exist?
- Capacity limitations, financial pressures

RISKS:
- Specific threats to supply continuity
- Geopolitical, operational, or financial risks

Return JSON:
{{
  "quantitative": {{
    "financial_scale": "Assessment",
    "capacity_assessment": "Assessment",
    "investment_outlook": "Assessment",
    "mutual_dependency": "Assessment"
  }},
  "qualitative": {{
    "strategic_importance": "Assessment",
    "relationship_strength": "Assessment",
    "risk_level": "High|Medium|Low",
    "alternative_availability": "Assessment"
  }},
  "opportunities": ["Opp 1", "Opp 2"],
  "challenges": ["Challenge 1", "Challenge 2"],
  "risks": ["Risk 1", "Risk 2"],
  "reliability_score": 7.5,
  "summary": "2-3 sentence executive summary"
}}"""
        
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
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
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
        
        # Factor 1: Importance (-1 to +1)
        importance = supplier.get('importance', 'Medium')
        if importance == 'Critical':
            score -= 1.0  # High concentration risk
        elif importance == 'High':
            score -= 0.5
        else:
            score += 0.5
        
        # Factor 2: Reliability score from analysis
        if impact_analysis.get('success'):
            reliability = impact_analysis.get('reliability_score', 5.0)
            score += (reliability - 5) / 5  # Normalize to -1 to +1
        
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
        
        # Factor 4: Risk assessment
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
        
        # Step 1: Identify suppliers via web search
        try:
            company = Company(ticker)
            company_name = company.name
        except:
            company_name = ticker.upper()
        
        supplier_search = self.identify_suppliers_with_web_search(ticker, company_name)
        
        if not supplier_search.get('success') or not supplier_search.get('suppliers'):
            return {
                'success': False,
                'error': supplier_search.get('error', 'No suppliers identified'),
                'ticker': ticker.upper()
            }
        
        suppliers = supplier_search['suppliers'][:5]
        
        if verbose:
            print(f"✅ Identified {len(suppliers)} suppliers via web search\n")
            print(f"Search Quality: {supplier_search.get('search_quality', 'Unknown')}\n")
            print("Step 2: Analyzing each supplier in detail...\n")
        
        # Step 2: Analyze each supplier
        analyzed_suppliers = []
        
        for i, supplier in enumerate(suppliers):
            if verbose:
                print(f"  [{i+1}/5] {supplier['name']}...")
            
            supplier_result = supplier.copy()
            
            # Only analyze if supplier is public (has ticker)
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
                
                # Calculate score
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
                    'error': 'Private company - no 10-K available'
                }
                supplier_result['score'] = -0.5  # Default for private suppliers
                
                if verbose:
                    print(f"     🔒 Private company - limited analysis")
            
            analyzed_suppliers.append(supplier_result)
        
        # Step 3: Calculate aggregate score
        scores = [s['score'] for s in analyzed_suppliers if 'score' in s]
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
            print(f"SUPPLIER RISK SCORE: {composite}/10")
            print(f"RISK LEVEL: {signal}")
            print(f"{'='*80}")
            print(f"API Usage: ~{self.total_tokens:,} tokens (~${self.total_tokens * 0.003 / 1000:.3f})")
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


# Test function
if __name__ == "__main__":
    import os
    
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    
    if not api_key:
        print("❌ Set ANTHROPIC_API_KEY environment variable")
    else:
        analyzer = SupplierAnalyzer(api_key)
        result = analyzer.analyze("NVDA")
        
        if result['success']:
            print(f"\n✅ Analysis Complete!")
            print(f"Risk Score: {result['score']}/10")
            print(f"Signal: {result['signal']}")
