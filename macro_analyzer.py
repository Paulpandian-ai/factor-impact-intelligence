"""
Macro Factors Analysis Module - Module 5
Analyzes geopolitical, regulatory, industry, commodity, and ESG factors
Combines deterministic data + probabilistic AI assessment
"""

from edgar import Company, set_identity
import anthropic
import os
from datetime import datetime
from typing import Dict
import json

# CHANGE THIS TO YOUR EMAIL
set_identity("Paul Balasubramanian pb2963@columbia.edu")


class MacroFactorAnalyzer:
    """Analyzes macro-level factors affecting stock performance"""
    
    def __init__(self, anthropic_api_key: str = None):
        """Initialize with Anthropic API key"""
        self.api_key = anthropic_api_key or os.environ.get('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("Anthropic API key required")
        
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.current_date = datetime.now()
        self.total_tokens = 0
    
    def analyze_geopolitical_risk(self, ticker: str, company_name: str) -> Dict:
        """Analyze geopolitical risks with web search"""
        
        prompt = f"""Search for geopolitical risks affecting {company_name} ({ticker}).

Search for:
- "{company_name} China export restrictions 2025"
- "{company_name} Taiwan risk"
- "{company_name} geopolitical sanctions tariffs"

Analyze:
1. Export Controls: Any restrictions on selling to China/Russia?
2. Tariffs: Active tariffs affecting the company?
3. Geographic Concentration: Heavy dependence on one country/region?
4. Conflict Risk: Exposure to Taiwan, Ukraine, Middle East?
5. Tension Assessment: Are geopolitical tensions escalating?

Return JSON (scores -2 to +2, negative is bad):
{{
  "export_controls": {{
    "status": "Active|None",
    "description": "Details",
    "score": -1.5
  }},
  "tariffs": {{
    "status": "Significant|Moderate|Minimal",
    "description": "Details",
    "score": -1.0
  }},
  "geographic_concentration": {{
    "status": "High|Medium|Low",
    "primary_exposure": "Country",
    "score": -1.0
  }},
  "conflict_risk": {{
    "level": "High|Medium|Low",
    "areas": ["Taiwan"],
    "score": -1.5
  }},
  "tension_assessment": {{
    "trend": "Escalating|Stable|De-escalating",
    "description": "Details",
    "score": -0.8
  }},
  "overall_score": -1.2,
  "key_risks": ["Risk 1", "Risk 2"],
  "summary": "2-3 sentences"
}}

ONLY return JSON."""
        
        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=3000,
                temperature=0,
                tools=[{"type": "web_search_20250305", "name": "web_search"}],
                messages=[{"role": "user", "content": prompt}]
            )
            
            self.total_tokens += message.usage.input_tokens + message.usage.output_tokens
            
            response_text = "".join([block.text for block in message.content if block.type == "text"])
            result = self._parse_json(response_text)
            
            return {'success': True, **result}
            
        except Exception as e:
            return {'success': False, 'error': str(e), 'overall_score': 0}
    
    def analyze_regulatory_risk(self, ticker: str, company_name: str) -> Dict:
        """Analyze regulatory and legal risks"""
        
        prompt = f"""Search for regulatory risks affecting {company_name} ({ticker}).

Search for:
- "{company_name} antitrust investigation 2025"
- "{company_name} regulatory fine lawsuit"
- "{company_name} industry regulation"

Analyze:
1. Active Investigations: Any DOJ, FTC, EU investigations?
2. Violations/Fines: Recent fines or penalties?
3. Regulatory Climate: Is regulatory scrutiny increasing?
4. Upcoming Legislation: New laws impacting operations?
5. Compliance Burden: Heavy compliance costs?

Return JSON:
{{
  "active_investigations": {{
    "status": "Active|None",
    "details": "Details",
    "score": -1.0
  }},
  "violations_fines": {{
    "status": "Recent|None",
    "amount": "$X" or "None",
    "score": -0.5
  }},
  "regulatory_climate": {{
    "trend": "Hostile|Neutral|Favorable",
    "description": "Details",
    "score": -0.7
  }},
  "upcoming_legislation": {{
    "impact": "Major|Minor|None",
    "description": "Details",
    "score": -0.5
  }},
  "overall_score": -0.6,
  "key_risks": ["Risk 1"],
  "summary": "2-3 sentences"
}}

ONLY return JSON."""
        
        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=3000,
                temperature=0,
                tools=[{"type": "web_search_20250305", "name": "web_search"}],
                messages=[{"role": "user", "content": prompt}]
            )
            
            self.total_tokens += message.usage.input_tokens + message.usage.output_tokens
            response_text = "".join([block.text for block in message.content if block.type == "text"])
            result = self._parse_json(response_text)
            
            return {'success': True, **result}
            
        except Exception as e:
            return {'success': False, 'error': str(e), 'overall_score': 0}
    
    def analyze_industry_dynamics(self, ticker: str, company_name: str) -> Dict:
        """Analyze industry trends"""
        
        prompt = f"""Search for industry dynamics affecting {company_name} ({ticker}).

Search for:
- "{company_name} industry outlook 2025"
- "{company_name} sector growth forecast"
- "{company_name} competitive landscape"

Analyze:
1. Industry Growth: Growing or declining?
2. Competitive Intensity: Competition intensifying?
3. Technology Cycle: Where in cycle (early/peak/mature)?
4. Pricing Power: Can raise prices?
5. Supply/Demand: Shortage or oversupply?

Return JSON (positive scores good):
{{
  "industry_growth": {{
    "rate": "High|Moderate|Low|Negative",
    "description": "Details",
    "score": 1.5
  }},
  "competitive_intensity": {{
    "trend": "Intensifying|Stable|Consolidating",
    "description": "Details",
    "score": 0.3
  }},
  "technology_cycle": {{
    "phase": "Early Growth|Peak|Maturity|Decline",
    "description": "Details",
    "score": 1.5
  }},
  "pricing_power": {{
    "level": "Strong|Moderate|Weak",
    "description": "Details",
    "score": 0.8
  }},
  "overall_score": 1.4,
  "key_trends": ["Trend 1"],
  "summary": "2-3 sentences"
}}

ONLY return JSON."""
        
        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=3000,
                temperature=0,
                tools=[{"type": "web_search_20250305", "name": "web_search"}],
                messages=[{"role": "user", "content": prompt}]
            )
            
            self.total_tokens += message.usage.input_tokens + message.usage.output_tokens
            response_text = "".join([block.text for block in message.content if block.type == "text"])
            result = self._parse_json(response_text)
            
            return {'success': True, **result}
            
        except Exception as e:
            return {'success': False, 'error': str(e), 'overall_score': 0}
    
    def analyze_commodity_risk(self, ticker: str, company_name: str) -> Dict:
        """Analyze commodity and input cost risks"""
        
        prompt = f"""Search for commodity risks affecting {company_name} ({ticker}).

Search for:
- "{company_name} energy costs supply chain"
- "{company_name} raw material prices"
- "{company_name} logistics freight costs"

Analyze:
1. Energy Exposure: High electricity/fuel costs?
2. Raw Material Prices: Exposure to commodities?
3. Logistics Costs: Shipping exposure?
4. Supply Chain Resilience: Vulnerable to disruptions?
5. Input Cost Trends: Rising or stable?

Return JSON:
{{
  "energy_exposure": {{
    "level": "High|Medium|Low",
    "description": "Details",
    "score": -0.5
  }},
  "raw_materials": {{
    "exposure": "High|Medium|Low",
    "trend": "Rising|Stable|Falling",
    "score": -0.3
  }},
  "logistics_costs": {{
    "level": "High|Normal|Low",
    "description": "Details",
    "score": 0
  }},
  "supply_chain_resilience": {{
    "assessment": "Vulnerable|Adequate|Robust",
    "score": 0.3
  }},
  "overall_score": 0.2,
  "key_risks": ["Risk 1"],
  "summary": "2-3 sentences"
}}

ONLY return JSON."""
        
        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=3000,
                temperature=0,
                tools=[{"type": "web_search_20250305", "name": "web_search"}],
                messages=[{"role": "user", "content": prompt}]
            )
            
            self.total_tokens += message.usage.input_tokens + message.usage.output_tokens
            response_text = "".join([block.text for block in message.content if block.type == "text"])
            result = self._parse_json(response_text)
            
            return {'success': True, **result}
            
        except Exception as e:
            return {'success': False, 'error': str(e), 'overall_score': 0}
    
    def analyze_esg_factors(self, ticker: str, company_name: str) -> Dict:
        """Analyze ESG and social factors"""
        
        prompt = f"""Search for ESG risks affecting {company_name} ({ticker}).

Search for:
- "{company_name} ESG controversy 2025"
- "{company_name} environmental violations"
- "{company_name} labor issues strike"

Analyze:
1. Environmental Issues: Violations, climate risk?
2. Social Issues: Labor problems, diversity?
3. Governance Issues: Scandals, board issues?
4. ESG Controversies: Major incidents?
5. Public Perception: Boycott risk?

Return JSON:
{{
  "environmental": {{
    "risk": "High|Medium|Low",
    "description": "Details",
    "score": -0.3
  }},
  "social": {{
    "risk": "High|Medium|Low",
    "description": "Details",
    "score": -0.2
  }},
  "governance": {{
    "risk": "High|Medium|Low",
    "description": "Details",
    "score": 0
  }},
  "controversies": {{
    "count": "Multiple|One|None",
    "description": "Details",
    "score": -0.5
  }},
  "overall_score": 0.1,
  "key_issues": ["Issue 1"],
  "summary": "2-3 sentences"
}}

ONLY return JSON."""
        
        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=3000,
                temperature=0,
                tools=[{"type": "web_search_20250305", "name": "web_search"}],
                messages=[{"role": "user", "content": prompt}]
            )
            
            self.total_tokens += message.usage.input_tokens + message.usage.output_tokens
            response_text = "".join([block.text for block in message.content if block.type == "text"])
            result = self._parse_json(response_text)
            
            return {'success': True, **result}
            
        except Exception as e:
            return {'success': False, 'error': str(e), 'overall_score': 0}
    
    def _parse_json(self, text: str) -> Dict:
        """Parse JSON from response"""
        text = text.strip()
        
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            text = text[start:end+1]
        
        return json.loads(text)
    
    def analyze(self, ticker: str, verbose: bool = True) -> Dict:
        """Complete macro factors analysis"""
        
        if verbose:
            print(f"\n{'='*80}")
            print(f"MACRO FACTORS ANALYSIS: {ticker.upper()}")
            print(f"{'='*80}\n")
        
        try:
            company = Company(ticker)
            company_name = company.name
        except:
            company_name = ticker.upper()
        
        if verbose:
            print("Analyzing macro factors...")
        
        # Analyze each category
        if verbose:
            print("  [1/5] Geopolitical Risk...")
        geopolitical = self.analyze_geopolitical_risk(ticker, company_name)
        
        if verbose:
            print("  [2/5] Regulatory Risk...")
        regulatory = self.analyze_regulatory_risk(ticker, company_name)
        
        if verbose:
            print("  [3/5] Industry Dynamics...")
        industry = self.analyze_industry_dynamics(ticker, company_name)
        
        if verbose:
            print("  [4/5] Commodity Risk...")
        commodity = self.analyze_commodity_risk(ticker, company_name)
        
        if verbose:
            print("  [5/5] ESG Factors...")
        esg = self.analyze_esg_factors(ticker, company_name)
        
        # Calculate weighted composite
        weights = {
            'geopolitical': 0.30,
            'regulatory': 0.25,
            'industry': 0.25,
            'commodity': 0.15,
            'esg': 0.05
        }
        
        composite_raw = (
            geopolitical.get('overall_score', 0) * weights['geopolitical'] +
            regulatory.get('overall_score', 0) * weights['regulatory'] +
            industry.get('overall_score', 0) * weights['industry'] +
            commodity.get('overall_score', 0) * weights['commodity'] +
            esg.get('overall_score', 0) * weights['esg']
        )
        
        # Convert to 1-10 scale
        composite = round(5.5 + (composite_raw * 2.25), 1)
        
        # Determine signal
        if composite >= 7.5:
            signal = "VERY FAVORABLE"
        elif composite >= 6.5:
            signal = "FAVORABLE"
        elif composite >= 5.5:
            signal = "NEUTRAL"
        elif composite >= 4.5:
            signal = "CHALLENGING"
        else:
            signal = "VERY CHALLENGING"
        
        if verbose:
            print(f"\n{'='*80}")
            print(f"MACRO ENVIRONMENT: {composite}/10")
            print(f"ASSESSMENT: {signal}")
            print(f"{'='*80}")
            print(f"Cost: ${self.total_tokens * 0.003 / 1000:.3f}")
            print(f"{'='*80}\n")
        
        return {
            'success': True,
            'ticker': ticker.upper(),
            'company_name': company_name,
            'score': composite,
            'signal': signal,
            'geopolitical': geopolitical,
            'regulatory': regulatory,
            'industry': industry,
            'commodity': commodity,
            'esg': esg,
            'weights': weights,
            'composite_raw': composite_raw,
            'tokens_used': self.total_tokens,
            'estimated_cost': self.total_tokens * 0.003 / 1000
        }
