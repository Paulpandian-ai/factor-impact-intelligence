"""
Enhanced Monetary Analyzer with Intelligent Caching
Fetches FRED data once per day, reuses cached data
"""

import yfinance as yf
from fredapi import Fred
import pandas as pd
from datetime import datetime, timedelta
from data_cache_manager import DataCacheManager, TTL_DAILY

class EnhancedMonetaryAnalyzer:
    """
    Analyzes monetary factors with intelligent caching
    
    Caching Strategy:
    - FRED data: Cached for 24 hours (updated daily)
    - Stock data: Cached for 24 hours
    - Beta calculation: Cached for 7 days (slow changing)
    """
    
    def __init__(self, fred_api_key: str):
        self.fred = Fred(api_key=fred_api_key)
        self.cache = DataCacheManager()
    
    def analyze(self, ticker: str, verbose: bool = False) -> dict:
        """Run complete monetary analysis with caching"""
        
        # Get stock data (cached 24h)
        stock_data, info = self._get_stock_data_cached(ticker)
        if stock_data is None:
            return {'success': False, 'error': 'No stock data available'}
        
        # Get beta (cached 7 days - slow changing)
        beta = self._get_beta_cached(ticker, stock_data, info)
        
        # Get FRED data (cached 24h - updates daily)
        fed_data = self._get_fed_rate_cached()
        inf_data = self._get_inflation_cached()
        yld_data = self._get_yield_cached()
        
        # Calculate scores (not cached - cheap computation)
        fed_scores = {
            "aggressive_tightening": -2.0, 
            "tightening": -1.0, 
            "aggressive_easing": 2.0, 
            "easing": 1.0, 
            "stable": 0.0
        }
        fed_score = fed_scores.get(fed_data['trend'], 0) if fed_data else 0
        
        inf_scores = {"high": -1.5, "elevated": -0.5, "target": 1.0, "low": 0.0}
        inf_score = inf_scores.get(inf_data['trend'], 0) if inf_data else 0
        
        yld_scores = {
            "rapid_rise": -2.0, 
            "rising": -1.0, 
            "rapid_fall": 2.0, 
            "falling": 1.0, 
            "stable": 0.0
        }
        yld_score = yld_scores.get(yld_data['trend'], 0) if yld_data else 0
        
        # Adjust for beta
        if beta > 1.5:
            fed_score = max(-2.0, min(2.0, fed_score * 1.3))
            inf_score = max(-2.0, min(2.0, inf_score * 1.2))
            yld_score = max(-2.0, min(2.0, yld_score * 1.3))
        
        # Calculate composite score
        weighted = (fed_score * 0.35) + (inf_score * 0.35) + (yld_score * 0.30)
        composite = round(5.5 + (weighted * 2.25), 1)
        
        if composite >= 7.5:
            signal = "STRONG BUY"
        elif composite >= 6.5:
            signal = "BUY"
        elif composite >= 5.5:
            signal = "HOLD"
        else:
            signal = "SELL"
        
        result = {
            'success': True,
            'ticker': ticker.upper(),
            'score': composite,
            'signal': signal,
            'beta': beta,
            'fed': fed_data,
            'inf': inf_data,
            'yld': yld_data,
            'fed_score': fed_score,
            'inf_score': inf_score,
            'yld_score': yld_score,
            '_cache_info': {
                'fed_cached': fed_data.get('_from_cache', False),
                'inf_cached': inf_data.get('_from_cache', False),
                'yld_cached': yld_data.get('_from_cache', False)
            }
        }
        
        if verbose:
            print(f"✅ Monetary analysis for {ticker}")
            print(f"   Fed data from cache: {result['_cache_info']['fed_cached']}")
            print(f"   Inflation from cache: {result['_cache_info']['inf_cached']}")
            print(f"   Yields from cache: {result['_cache_info']['yld_cached']}")
        
        return result
    
    def _get_stock_data_cached(self, ticker: str):
        """Get stock data with 24h cache"""
        
        def fetch_stock_data():
            try:
                stock = yf.Ticker(ticker)
                end = datetime.now()
                start = end - timedelta(days=365)
                hist = stock.history(start=start, end=end)
                
                if hist.empty:
                    return {'success': False, 'data': None, 'info': None}
                
                return {
                    'success': True,
                    'data': hist.to_dict(),
                    'info': stock.info
                }
            except Exception as e:
                return {'success': False, 'error': str(e)}
        
        cache_key = f"stock_data:{ticker}"
        cached = self.cache.get(
            cache_key=cache_key,
            fetch_function=fetch_stock_data,
            ttl_hours=TTL_DAILY,
            data_type="stock_data",
            ticker=ticker
        )
        
        if not cached.get('success'):
            return None, None
        
        # Reconstruct DataFrame
        hist = pd.DataFrame(cached['data'])
        if 'Date' in hist.columns:
            hist['Date'] = pd.to_datetime(hist['Date'])
            hist.set_index('Date', inplace=True)
        
        return hist, cached['info']
    
    def _get_beta_cached(self, ticker: str, stock_data: pd.DataFrame, info: dict):
        """Get beta with 7-day cache (slow changing)"""
        
        def calculate_beta():
            try:
                # Try from info first
                if 'beta' in info and info['beta']:
                    return {'beta': float(info['beta'])}
                
                # Calculate manually
                returns = stock_data['Close'].pct_change().dropna()
                spy = yf.Ticker('SPY')
                spy_hist = spy.history(start=stock_data.index[0], end=stock_data.index[-1])
                spy_returns = spy_hist['Close'].pct_change().dropna()
                
                aligned = pd.DataFrame({'stock': returns, 'market': spy_returns}).dropna()
                
                if len(aligned) < 30:
                    return {'beta': 1.0}
                
                beta = aligned.cov().loc['stock', 'market'] / aligned['market'].var()
                return {'beta': float(beta)}
                
            except:
                return {'beta': 1.0}
        
        cache_key = f"beta:{ticker}"
        cached = self.cache.get(
            cache_key=cache_key,
            fetch_function=calculate_beta,
            ttl_hours=24 * 7,  # 7 days
            data_type="beta",
            ticker=ticker
        )
        
        return cached['beta']
    
    def _get_fed_rate_cached(self):
        """Get Fed rate with 24h cache"""
        
        def fetch_fed_rate():
            try:
                end = datetime.now()
                start = end - timedelta(days=365)
                data = self.fred.get_series('FEDFUNDS', observation_start=start, observation_end=end)
                
                if data.empty:
                    return {'success': False}
                
                current = float(data.iloc[-1])
                prev = float(data.iloc[-4] if len(data) >= 4 else data.iloc[0])
                change = current - prev
                
                if change > 0.25:
                    trend = "aggressive_tightening"
                elif change > 0:
                    trend = "tightening"
                elif change < -0.25:
                    trend = "aggressive_easing"
                elif change < 0:
                    trend = "easing"
                else:
                    trend = "stable"
                
                return {
                    'success': True,
                    'current': current,
                    'change': change,
                    'trend': trend
                }
            except Exception as e:
                return {'success': False, 'error': str(e)}
        
        cache_key = "fred:fedfunds"
        return self.cache.get(
            cache_key=cache_key,
            fetch_function=fetch_fed_rate,
            ttl_hours=TTL_DAILY,
            data_type="fred_rate",
            ticker=None
        )
    
    def _get_inflation_cached(self):
        """Get inflation with 24h cache"""
        
        def fetch_inflation():
            try:
                end = datetime.now()
                start = end - timedelta(days=365)
                cpi = self.fred.get_series('CPIAUCSL', observation_start=start, observation_end=end)
                
                if cpi.empty or len(cpi) < 12:
                    return {'success': False}
                
                current = float(cpi.iloc[-1])
                prev = float(cpi.iloc[-13] if len(cpi) >= 13 else cpi.iloc[0])
                yoy = ((current - prev) / prev) * 100
                
                if yoy > 4.0:
                    trend = "high"
                elif yoy > 2.5:
                    trend = "elevated"
                elif yoy >= 1.5:
                    trend = "target"
                else:
                    trend = "low"
                
                return {
                    'success': True,
                    'yoy': yoy,
                    'trend': trend
                }
            except Exception as e:
                return {'success': False, 'error': str(e)}
        
        cache_key = "fred:cpi"
        return self.cache.get(
            cache_key=cache_key,
            fetch_function=fetch_inflation,
            ttl_hours=TTL_DAILY,
            data_type="fred_cpi",
            ticker=None
        )
    
    def _get_yield_cached(self):
        """Get 10Y yield with 24h cache"""
        
        def fetch_yield():
            try:
                end = datetime.now()
                start = end - timedelta(days=365)
                data = self.fred.get_series('DGS10', observation_start=start, observation_end=end).dropna()
                
                if data.empty:
                    return {'success': False}
                
                current = float(data.iloc[-1])
                prev = float(data.iloc[-22] if len(data) >= 22 else data.iloc[0])
                change = current - prev
                
                if change > 0.5:
                    trend = "rapid_rise"
                elif change > 0.1:
                    trend = "rising"
                elif change < -0.5:
                    trend = "rapid_fall"
                elif change < -0.1:
                    trend = "falling"
                else:
                    trend = "stable"
                
                return {
                    'success': True,
                    'current': current,
                    'change': change,
                    'trend': trend
                }
            except Exception as e:
                return {'success': False, 'error': str(e)}
        
        cache_key = "fred:dgs10"
        return self.cache.get(
            cache_key=cache_key,
            fetch_function=fetch_yield,
            ttl_hours=TTL_DAILY,
            data_type="fred_yield",
            ticker=None
        )
