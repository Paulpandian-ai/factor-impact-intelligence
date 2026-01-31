"""
Supplier Analysis Module - Simplified Working Version
"""

from edgar import Company, set_identity
import anthropic
import os

# CHANGE THIS TO YOUR EMAIL
set_identity("Paul Balasubramanian pb2963@columbia.edu")


class SupplierAnalyzer:
    """Analyzes supplier relationships using Claude AI"""
    
    def __init__(self, anthropic_api_key=None):
        self.api_key = anthropic_api_key or os.environ.get('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("Anthropic API key required")
        self.client = anthropic.Anthropic(api_key=self.api_key)
    
    def analyze(self, ticker, verbose=True):
        """Analyze supplier relationships for a ticker"""
        
        try:
            # Get company
            company = Company(ticker)
            
            # Get 10-K filing
            filing = None
            try:
                filings = company.get_filings(form="10-K")
                for f in filings:
                    filing = f
                    break
            except:
                pass
            
            if not filing:
                return {
                    'success': False,
                    'error': f'No 10-K filing found for {ticker}',
                    'ticker': ticker.upper()
                }
            
            # Get text
            try:
                text = filing.text()
            except:
                try:
                    text = str(filing.html())
                except:
                    return {
                        'success': False,
                        'error': 'Could not extract filing text',
                        'ticker': ticker.upper()
                    }
            
            # Use Claude to extract suppliers
            prompt = f"""Analyze this 10-K excerpt and identify the top 5 suppliers.

Return JSON format:
{{
  "suppliers": [
    {{
      "name": "Supplier Name",
      "ticker": "TICK or PRIVATE",
      "supplies": "What they provide",
      "importance": "Critical/High/Medium",
      "revenue_exposure": "% if mentioned",
      "risks": ["Risk 1", "Risk 2"],
      "relationship_notes": "Brief context",
      "quote": "Quote if available"
    }}
  ],
  "overall_supplier_risk": "High/Medium/Low",
  "key_findings": ["Finding 1", "Finding 2"]
}}

Text excerpt:
{text[:25000]}"""
            
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=3000,
                temperature=0,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response = message.content[0].text.strip()
            
            # Clean JSON
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            import json
            result = json.loads(response)
            
            suppliers = result.get('suppliers', [])[:5]
            
            # Score each supplier
            for s in suppliers:
                importance = s.get('importance', 'Medium')
                if importance == 'Critical':
                    s['score'] = -1.0
                elif importance == 'High':
                    s['score'] = -0.5
                else:
                    s['score'] = 0.5
            
            # Calculate composite score
            if suppliers:
                avg_score = sum(s['score'] for s in suppliers) / len(suppliers)
                composite = round(5.5 + (avg_score * 2.25), 1)
            else:
                composite = 5.0
            
            if composite >= 7.0:
                signal = "LOW RISK"
            elif composite >= 5.5:
                signal = "MODERATE RISK"
            else:
                signal = "HIGH RISK"
            
            return {
                'success': True,
                'ticker': ticker.upper(),
                'company_name': company.name,
                'score': composite,
                'signal': signal,
                'confidence': 'Medium',
                'overall_supplier_risk': result.get('overall_supplier_risk', 'Medium'),
                'key_findings': result.get('key_findings', []),
                'suppliers': suppliers,
                'filing_date': str(filing.filing_date),
                'tokens_used': message.usage.input_tokens + message.usage.output_tokens,
                'estimated_cost': (message.usage.input_tokens + message.usage.output_tokens) * 0.003 / 1000
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Analysis failed: {str(e)}',
                'ticker': ticker.upper()
            }
