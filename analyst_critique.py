"""
Analyst Critique Module - Module 8
Extracts analyst thesis from reports and critiques against our comprehensive data
"""

import anthropic
import os
from typing import Dict, Optional
import json
import base64

class AnalystCritique:
    """Critiques analyst reports against our 5-module analysis"""
    
    def __init__(self, anthropic_api_key: Optional[str] = None):
        """Initialize with Anthropic API key"""
        self.api_key = anthropic_api_key or os.environ.get('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("Anthropic API key required")
        
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.total_tokens = 0
    
    def extract_analyst_thesis(self, pdf_data: bytes, filename: str) -> Dict:
        """Extract analyst's thesis from uploaded PDF"""
        
        # Convert PDF to base64
        pdf_base64 = base64.standard_b64encode(pdf_data).decode('utf-8')
        
        prompt = """Analyze this analyst report and extract key information.

Extract:
1. **Analyst Firm**: Who published this (Morningstar, Goldman Sachs, etc.)
2. **Report Date**: When was this published
3. **Stock Ticker**: Which stock (NVDA, GOOGL, AMZN, TSLA, etc.)
4. **Rating**: What's their recommendation (5-star, 4-star, Buy, Hold, Sell, etc.)
5. **Price Target**: If mentioned, what price target
6. **Fair Value**: Their estimate of fair value
7. **Current Price**: Stock price at report date
8. **Economic Moat**: Wide, Narrow, None
9. **Key Investment Thesis**: Main bull case (2-3 key points)
10. **Growth Expectations**: Revenue/earnings growth forecasts
11. **Risks Identified**: What risks did they mention
12. **Competitive Position**: How do they view competition
13. **Valuation Metrics**: P/E, P/S, etc. mentioned

Return ONLY valid JSON:
{
  "analyst_firm": "Morningstar",
  "report_date": "2026-01-30",
  "ticker": "NVDA",
  "rating": "4 stars",
  "price_target": null,
  "fair_value": 240.00,
  "current_price": 191.13,
  "economic_moat": "Wide",
  "key_thesis": ["Point 1", "Point 2", "Point 3"],
  "growth_expectations": {
    "revenue_1yr": "114.2%",
    "earnings_1yr": "147.1%"
  },
  "risks_identified": ["Risk 1", "Risk 2"],
  "competitive_position": "Dominant in AI GPUs",
  "valuation_metrics": {
    "pe_ratio": 47.3,
    "forward_pe": 24.9,
    "price_sales": 25.1
  },
  "profitability": {
    "gross_margin": "70.1%",
    "operating_margin": "58.8%",
    "net_margin": "53.0%"
  }
}"""
        
        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                temperature=0,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": pdf_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }]
            )
            
            self.total_tokens += message.usage.input_tokens + message.usage.output_tokens
            
            # Extract response
            response_text = ""
            for block in message.content:
                if block.type == "text":
                    response_text += block.text
            
            # Clean JSON
            response_text = response_text.strip()
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]
            
            start = response_text.find('{')
            end = response_text.rfind('}')
            if start != -1 and end != -1:
                response_text = response_text[start:end+1]
            
            result = json.loads(response_text)
            
            return {
                'success': True,
                **result
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def compare_with_platform_data(self, analyst_thesis: Dict, platform_data: Dict) -> Dict:
        """Compare analyst's thesis with our comprehensive 5-module data"""
        
        ticker = analyst_thesis.get('ticker', 'UNKNOWN')
        
        # Build our data summary
        our_data = f"""
TICKER: {ticker}

OUR 5-MODULE ANALYSIS:

1. MONETARY FACTORS:
   Score: {platform_data.get('monetary', {}).get('score', 'N/A')}/10
   Signal: {platform_data.get('monetary', {}).get('signal', 'N/A')}

2. COMPANY PERFORMANCE:
   Score: {platform_data.get('company', {}).get('score', 'N/A')}/10
   Signal: {platform_data.get('company', {}).get('signal', 'N/A')}

3. SUPPLIER ANALYSIS:
   Score: {platform_data.get('suppliers', {}).get('score', 'N/A')}/10
   Risk Level: {platform_data.get('suppliers', {}).get('signal', 'N/A')}
   Key Findings: {platform_data.get('suppliers', {}).get('key_findings', [])}

4. CUSTOMER ANALYSIS:
   Score: {platform_data.get('customers', {}).get('score', 'N/A')}/10
   Demand: {platform_data.get('customers', {}).get('signal', 'N/A')}
   Key Findings: {platform_data.get('customers', {}).get('key_findings', [])}

5. MACRO FACTORS:
   Score: {platform_data.get('macro', {}).get('score', 'N/A')}/10
   Assessment: {platform_data.get('macro', {}).get('signal', 'N/A')}

OVERALL COMBINED SCORE: {platform_data.get('combined_score', 'N/A')}/10
OVERALL SIGNAL: {platform_data.get('combined_signal', 'N/A')}
"""
        
        analyst_summary = f"""
ANALYST'S VIEW ({analyst_thesis.get('analyst_firm', 'Unknown')}):

Report Date: {analyst_thesis.get('report_date', 'Unknown')}
Rating: {analyst_thesis.get('rating', 'Unknown')}
Fair Value: ${analyst_thesis.get('fair_value', 'N/A')}
Current Price: ${analyst_thesis.get('current_price', 'N/A')}
Economic Moat: {analyst_thesis.get('economic_moat', 'N/A')}

Key Thesis:
{chr(10).join(['• ' + t for t in analyst_thesis.get('key_thesis', [])])}

Growth Expectations:
{json.dumps(analyst_thesis.get('growth_expectations', {}), indent=2)}

Risks Identified:
{chr(10).join(['• ' + r for r in analyst_thesis.get('risks_identified', [])])}

Valuation Metrics:
{json.dumps(analyst_thesis.get('valuation_metrics', {}), indent=2)}
"""
        
        prompt = f"""You are an expert financial analyst reviewing another analyst's report.

{analyst_summary}

{our_data}

Compare the analyst's view with our comprehensive 5-module data and generate a critique.

Structure your response as JSON:

{{
  "agreement_areas": [
    {{
      "topic": "Strong AI Demand",
      "analyst_view": "What analyst said",
      "our_data": "What our data shows",
      "verdict": "AGREE"
    }}
  ],
  "missed_factors": [
    {{
      "factor": "Supply Chain Concentration",
      "why_important": "90% TSMC dependency",
      "impact": "Material risk not in valuation",
      "severity": "High|Medium|Low"
    }}
  ],
  "underweighted_risks": [
    {{
      "risk": "Geopolitical Risk",
      "analyst_treatment": "Mentioned briefly",
      "our_assessment": "High risk - China export ban",
      "gap": "Should reduce PT by $10-15"
    }}
  ],
  "overweighted_factors": [
    {{
      "factor": "If any",
      "explanation": "Why analyst gave too much weight"
    }}
  ],
  "our_adjusted_view": {{
    "price_target": "Our estimate",
    "rating": "Our rating",
    "key_differences": ["Difference 1", "Difference 2"],
    "reasoning": "Why we differ"
  }},
  "factor_by_factor": {{
    "fundamentals": {{"agreement": "Agree|Disagree", "gap": "Explanation"}},
    "growth": {{"agreement": "Agree|Disagree", "gap": "Explanation"}},
    "risks": {{"agreement": "Agree|Disagree", "gap": "Explanation"}},
    "valuation": {{"agreement": "Agree|Disagree", "gap": "Explanation"}}
  }},
  "critique_summary": "2-3 paragraph executive summary of critique"
}}

Be specific, quantitative where possible, and give credit where analyst got things right!"""
        
        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=6000,
                temperature=0,
                messages=[{"role": "user", "content": prompt}]
            )
            
            self.total_tokens += message.usage.input_tokens + message.usage.output_tokens
            
            response_text = ""
            for block in message.content:
                if block.type == "text":
                    response_text += block.text
            
            # Clean JSON
            response_text = response_text.strip()
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]
            
            start = response_text.find('{')
            end = response_text.rfind('}')
            if start != -1 and end != -1:
                response_text = response_text[start:end+1]
            
            result = json.loads(response_text)
            
            return {
                'success': True,
                **result
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def generate_critique(self, pdf_data: bytes, filename: str, platform_data: Dict) -> Dict:
        """Complete critique workflow"""
        
        # Step 1: Extract analyst thesis
        thesis = self.extract_analyst_thesis(pdf_data, filename)
        
        if not thesis.get('success'):
            return {
                'success': False,
                'error': thesis.get('error', 'Failed to extract thesis')
            }
        
        # Step 2: Compare with platform data
        critique = self.compare_with_platform_data(thesis, platform_data)
        
        if not critique.get('success'):
            return {
                'success': False,
                'error': critique.get('error', 'Failed to generate critique')
            }
        
        # Combine results
        return {
            'success': True,
            'analyst_thesis': thesis,
            'critique': critique,
            'tokens_used': self.total_tokens,
            'estimated_cost': self.total_tokens * 0.003 / 1000
        }
