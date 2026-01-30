"""
Supplier Analysis Module - Module 2 (FIXED)
Uses Claude AI to identify and analyze supplier relationships
"""

from edgar import Company, set_identity
import anthropic
import os
import pandas as pd
from datetime import datetime, timedelta
import yfinance as yf
import re
from typing import List, Dict, Optional

# Set Edgar identity
set_identity("Paul Balasubramanian pb2963@columbia.edu")


class SupplierAnalyzer:
    """
    Analyzes supplier relationships using Claude AI + SEC filings
    """
    
    def __init__(self, anthropic_api_key: Optional[str] = None):
        """Initialize with Anthropic API key"""
        self.api_key = anthropic_api_key or os.environ.get('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("Anthropic API key required")
        
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.current_date = datetime.now()
    
    def get_company_10k(self, ticker: str) -> Optional[Dict]:
        """Fetch the latest 10-K filing"""
        try:
            company = Company(ticker)
            
            # Get latest 10-K filings
            tenk_filings = company.get_filings(form="10-K").latest(1)
            
            if not tenk_filings or len(tenk_filings) == 0:
                return {
                    'success': False,
                    'error': 'No 10-K filings found',
                    'ticker': ticker.upper()
                }
            
            # Get the first filing from the Filings object
            filing = None
            for f in tenk_filings:
                filing = f
                break
            
            if not filing:
                return {
                    'success': False,
                    'error': 'Could not access filing',
                    'ticker': ticker.upper()
                }
            
            # Get full text (this may take a moment)
            try:
                full_text = filing.text()
            except:
                # Fallback: try to get HTML and extract text
                try:
                    full_text = str(filing.html())
                except:
                    return {
                        'success': False,
                        'error': 'Could not extract filing text',
                        'ticker': ticker.upper()
                    }
            
            return {
                'success': True,
                'company_name': company.name,
                'ticker': ticker.upper(),
                'filing_date': str(filing.filing_date),
                'full_text': full_text[:500000],  # Limit to ~500K chars for API limits
                'accession_number': filing.accession_number
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Error fetching 10-K: {str(e)}",
                'ticker': ticker.upper()
            }
    
    def extract_suppliers_with_ai(self, company_name: str, filing_text: str) -> Dict:
        """
        Use Claude to extract top suppliers from 10-K filing
        """
        
        # Craft a detailed prompt for supplier extraction
        prompt = f"""You are a financial analyst expert at reading SEC 10-K filings.

Analyze this excerpt from {company_name}'s 10-K filing and identify the TOP 5 most critical suppliers.

For each supplier, extract:
1. Supplier name (exact company name)
2. What they supply (products/services/components)
3. Importance level (Critical/High/Medium) based on:
   - Revenue dependency mentioned
   - Whether described as "sole source" or "single source"
   - Frequency of mentions in risk factors
   - Supply chain criticality
4. Key risks (concentration, geographic, operational, financial)
5. Relationship context (any quotes about the relationship)

IMPORTANT GUIDELINES:
- Focus on ACTUAL suppliers (not customers, partners, or competitors)
- Look for mentions in "Business" section, "Risk Factors", and "MD&A"
- Prioritize suppliers with revenue exposure percentages
- Include semiconductor foundries, component manufacturers, raw material suppliers
- Ignore generic suppliers (e.g., "office supply vendors")

Filing excerpt:
{filing_text[:30000]}

Respond in this EXACT JSON format:
{{
  "suppliers": [
    {{
      "name": "Company Name",
      "ticker": "TICK" (if publicly traded, else "PRIVATE"),
      "supplies": "What they provide",
      "importance": "Critical|High|Medium",
      "revenue_exposure": "X%" (if mentioned, else "Not disclosed"),
      "risks": ["Risk 1", "Risk 2"],
      "relationship_notes": "Key context from filing",
      "quote": "Exact quote from filing if available"
    }}
  ],
  "overall_supplier_risk": "High|Medium|Low",
  "key_findings": ["Finding 1", "Finding 2", "Finding 3"]
}}

Only return valid JSON, no other text."""

        try:
            # Call Claude API
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                temperature=0,  # Deterministic for factual extraction
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Extract JSON from response
            response_text = message.content[0].text
            
            # Clean up response (remove markdown if present)
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            # Parse JSON
            import json
            result = json.loads(response_text)
            
            return {
                'success': True,
                'suppliers': result.get('suppliers', []),
                'overall_risk': result.get('overall_supplier_risk', 'Medium'),
                'key_findings': result.get('key_findings', []),
                'tokens_used': message.usage.input_tokens + message.usage.output_tokens
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"AI extraction failed: {str(e)}",
                'suppliers': []
            }
    
    def get_supplier_financials(self, supplier_ticker: str) -> Optional[Dict]:
        """Get financial metrics for a supplier"""
        if supplier_ticker == "PRIVATE" or not supplier_ticker:
            return None
        
        try:
            stock = yf.Ticker(supplier_ticker)
            info = stock.info
            
            # Get quarterly financials
            income_stmt = stock.quarterly_financials
            
            if income_stmt.empty:
                return None
            
            latest_qtr = income_stmt.columns[0]
            
            metrics = {
                'ticker': supplier_ticker,
                'company_name': info.get('longName', supplier_ticker),
                'market_cap': info.get('marketCap'),
                'revenue': income_stmt.loc['Total Revenue'].iloc[0] if 'Total Revenue' in income_stmt.index else None,
                'net_income': income_stmt.loc['Net Income'].iloc[0] if 'Net Income' in income_stmt.index else None,
                'profit_margin': info.get('profitMargins'),
                'debt_to_equity': info.get('debtToEquity'),
                'current_ratio': info.get('currentRatio'),
                'stock_price': info.get('currentPrice'),
                'latest_quarter': latest_qtr
            }
            
            return metrics
            
        except Exception as e:
            return None
    
    def get_supplier_10k_mda(self, supplier_ticker: str) -> Optional[str]:
        """Fetch MD&A section from supplier's latest 10-K"""
        if supplier_ticker == "PRIVATE" or not supplier_ticker:
            return None
        
        try:
            company = Company(supplier_ticker)
            
            # Try 10-K first
            tenk = company.get_filings(form="10-K").latest(1)
            
            filing = None
            if tenk and len(tenk) > 0:
                for f in tenk:
                    filing = f
                    break
            else:
                # Try 10-Q if 10-K not available
                tenq = company.get_filings(form="10-Q").latest(1)
                if tenq and len(tenq) > 0:
                    for f in tenq:
                        filing = f
                        break
            
            if not filing:
                return None
            
            # Get full text
            try:
                full_text = filing.text()
            except:
                try:
                    full_text = str(filing.html())
                except:
                    return None
            
            # Extract MD&A section (Item 7 for 10-K, Item 2 for 10-Q)
            # Simple regex extraction - Claude will analyze the content
            mda_pattern = r"(?:ITEM\s+7|Item\s+7)\.?\s*(?:MANAGEMENT|Management).{0,500}?(?=ITEM\s+[78]|Item\s+[78]|$)"
            mda_match = re.search(mda_pattern, full_text, re.DOTALL | re.IGNORECASE)
            
            if mda_match:
                mda_text = full_text[mda_match.start():mda_match.start()+20000]  # First 20K chars
                return mda_text
            
            # Fallback: return first chunk that might contain MD&A
            return full_text[:15000]
            
        except Exception as e:
            return None
    
    def analyze_supplier_mda_with_ai(self, supplier_name: str, mda_text: str) -> Dict:
        """Use Claude to analyze supplier's MD&A for risks and outlook"""
        
        prompt = f"""You are a financial analyst reviewing {supplier_name}'s MD&A (Management Discussion & Analysis) section.

Analyze this MD&A excerpt and provide:

1. **Financial Health Assessment** (Healthy/Concerning/Deteriorating)
   - Revenue trends
   - Profitability trends
   - Liquidity situation

2. **Key Risks Identified** (list 3-5 critical risks)
   - Operational risks
   - Market risks
   - Financial risks

3. **Forward Outlook** (Positive/Neutral/Negative)
   - Management's guidance
   - Growth expectations
   - Planned investments or restructuring

4. **Supply Chain Reliability Score** (1-10)
   - Based on operational stability
   - Financial strength
   - Risk exposure

5. **Red Flags** (if any)
   - Warning signs
   - Deteriorating metrics
   - Major uncertainties

MD&A Text:
{mda_text[:8000]}

Respond in this EXACT JSON format:
{{
  "financial_health": "Healthy|Concerning|Deteriorating",
  "health_reasoning": "Brief explanation",
  "key_risks": ["Risk 1", "Risk 2", "Risk 3"],
  "forward_outlook": "Positive|Neutral|Negative",
  "outlook_reasoning": "Brief explanation",
  "reliability_score": 7.5,
  "red_flags": ["Flag 1", "Flag 2"] or [],
  "summary": "2-3 sentence executive summary"
}}

Only return valid JSON."""

        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                temperature=0,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            response_text = message.content[0].text.strip()
            
            # Clean markdown
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            import json
            result = json.loads(response_text)
            
            return {
                'success': True,
                **result,
                'tokens_used': message.usage.input_tokens + message.usage.output_tokens
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def score_supplier(self, supplier_data: Dict, financials: Optional[Dict], mda_analysis: Optional[Dict]) -> float:
        """Calculate composite supplier score (-2 to +2)"""
        
        score = 0.0
        
        # Factor 1: Importance/Criticality (-1 to +1)
        importance = supplier_data.get('importance', 'Medium')
        if importance == 'Critical':
            score -= 1.0  # Critical suppliers are a RISK (concentration)
        elif importance == 'High':
            score -= 0.5
        else:
            score += 0.5  # Diversified suppliers are good
        
        # Factor 2: Financial Health (0 to +1)
        if mda_analysis and mda_analysis.get('success'):
            health = mda_analysis.get('financial_health', 'Neutral')
            if health == 'Healthy':
                score += 1.0
            elif health == 'Concerning':
                score -= 0.5
            elif health == 'Deteriorating':
                score -= 1.5
        
        # Factor 3: Reliability Score (0 to +1)
        if mda_analysis and mda_analysis.get('reliability_score'):
            reliability = mda_analysis['reliability_score']
            score += (reliability - 5) / 5  # Normalize to -1 to +1
        
        # Factor 4: Red Flags (-1 per flag, max -2)
        if mda_analysis and mda_analysis.get('red_flags'):
            flags = len(mda_analysis['red_flags'])
            score -= min(flags * 0.5, 2.0)
        
        # Factor 5: Financial Metrics
        if financials:
            # Profit margin
            margin = financials.get('profit_margin')
            if margin:
                if margin > 0.15:
                    score += 0.5
                elif margin < 0.05:
                    score -= 0.5
            
            # Debt to equity
            de = financials.get('debt_to_equity')
            if de:
                if de < 0.5:
                    score += 0.3
                elif de > 2.0:
                    score -= 0.5
        
        # Clamp to -2 to +2
        return max(-2.0, min(2.0, score))
    
    def analyze(self, ticker: str, verbose: bool = True) -> Dict:
        """
        Complete supplier analysis workflow
        """
        
        if verbose:
            print(f"\n{'='*80}")
            print(f"SUPPLIER ANALYSIS: {ticker.upper()}")
            print(f"Analysis Date: {self.current_date.strftime('%Y-%m-%d')}")
            print(f"{'='*80}\n")
            print("Step 1: Fetching company 10-K filing...")
        
        # Step 1: Get target company's 10-K
        filing_data = self.get_company_10k(ticker)
        
        if not filing_data or not filing_data.get('success'):
            return {
                'success': False,
                'error': filing_data.get('error', 'Could not fetch 10-K'),
                'ticker': ticker.upper()
            }
        
        if verbose:
            print(f"✅ Retrieved 10-K filed on {filing_data['filing_date']}\n")
            print("Step 2: Using Claude AI to identify suppliers...")
        
        # Step 2: Extract suppliers using Claude
        supplier_extraction = self.extract_suppliers_with_ai(
            filing_data['company_name'],
            filing_data['full_text']
        )
        
        if not supplier_extraction.get('success'):
            return {
                'success': False,
                'error': supplier_extraction.get('error', 'Supplier extraction failed'),
                'ticker': ticker.upper()
            }
        
        suppliers = supplier_extraction['suppliers'][:5]  # Top 5
        
        if verbose:
            print(f"✅ Identified {len(suppliers)} key suppliers\n")
            print("Step 3: Analyzing each supplier...\n")
        
        # Step 3: Analyze each supplier
        analyzed_suppliers = []
        total_tokens = supplier_extraction.get('tokens_used', 0)
        
        for i, supplier in enumerate(suppliers):
            if verbose:
                print(f"  [{i+1}/5] {supplier['name']}...")
            
            supplier_result = supplier.copy()
            
            # Get financials if publicly traded
            if supplier['ticker'] != 'PRIVATE':
                financials = self.get_supplier_financials(supplier['ticker'])
                supplier_result['financials'] = financials
                
                # Get MD&A
                mda_text = self.get_supplier_10k_mda(supplier['ticker'])
                
                if mda_text:
                    # Analyze MD&A with Claude
                    mda_analysis = self.analyze_supplier_mda_with_ai(supplier['name'], mda_text)
                    supplier_result['mda_analysis'] = mda_analysis
                    
                    if mda_analysis.get('success'):
                        total_tokens += mda_analysis.get('tokens_used', 0)
                else:
                    supplier_result['mda_analysis'] = None
            else:
                supplier_result['financials'] = None
                supplier_result['mda_analysis'] = None
            
            # Calculate score
            score = self.score_supplier(
                supplier_result,
                supplier_result.get('financials'),
                supplier_result.get('mda_analysis')
            )
            supplier_result['score'] = score
            
            analyzed_suppliers.append(supplier_result)
            
            if verbose:
                status = "✅" if score > 0 else "⚠️" if score > -1 else "❌"
                print(f"     {status} Score: {score:+.1f}/2.0")
        
        # Step 4: Calculate aggregate score
        if analyzed_suppliers:
            avg_score = sum(s['score'] for s in analyzed_suppliers) / len(analyzed_suppliers)
        else:
            avg_score = 0
        
        # Convert to 1-10 scale
        composite_score = round(5.5 + (avg_score * 2.25), 1)
        
        # Determine signal
        if composite_score >= 7.0:
            signal = "LOW RISK"
            confidence = "High"
        elif composite_score >= 5.5:
            signal = "MODERATE RISK"
            confidence = "Medium"
        elif composite_score >= 4.0:
            signal = "ELEVATED RISK"
            confidence = "Medium"
        else:
            signal = "HIGH RISK"
            confidence = "High"
        
        if verbose:
            print(f"\n{'='*80}")
            print(f"SUPPLIER RISK SCORE: {composite_score}/10")
            print(f"RISK LEVEL: {signal}")
            print(f"CONFIDENCE: {confidence}")
            print(f"{'='*80}")
            print(f"API Usage: ~{total_tokens:,} tokens (~${total_tokens * 0.003 / 1000:.3f})")
            print(f"{'='*80}\n")
        
        return {
            'success': True,
            'ticker': ticker.upper(),
            'company_name': filing_data['company_name'],
            'score': composite_score,
            'signal': signal,
            'confidence': confidence,
            'overall_supplier_risk': supplier_extraction.get('overall_risk', 'Medium'),
            'key_findings': supplier_extraction.get('key_findings', []),
            'suppliers': analyzed_suppliers,
            'filing_date': filing_data['filing_date'],
            'tokens_used': total_tokens,
            'estimated_cost': total_tokens * 0.003 / 1000  # $3 per 1M input tokens
        }
