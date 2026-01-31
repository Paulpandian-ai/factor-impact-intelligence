"""
Intelligent Data Cache Manager
Enterprise-grade caching with freshness tracking and cost optimization
"""

import sqlite3
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, Tuple
import os

class DataCacheManager:
    """
    Manages intelligent caching of all data with freshness tracking
    """
    
    # Data freshness rules (in hours)
    FRESHNESS_RULES = {
        # Real-time data (always fetch)
        'stock_price_current': 0,  # Always fresh
        'breaking_news': 0,  # Always fresh
        'earnings_day': 0,  # Always fresh on earnings day
        
        # Daily data (24 hour cache)
        'fed_rate': 24,
        'inflation': 24,
        'treasury_yield': 24,
        'stock_fundamentals': 24,
        
        # Weekly data (7 day cache)
        'macro_trends': 168,  # 7 days
        'regulatory_updates': 168,
        'industry_dynamics': 168,
        'esg_analysis': 168,
        
        # Quarterly data (90 day cache)
        'financial_statements': 2160,  # 90 days
        'supplier_relationships': 2160,
        'customer_relationships': 2160,
        'competitive_landscape': 2160,
        
        # Static data (cache indefinitely)
        'company_profile': 8760,  # 1 year
        'business_model': 8760,
        'industry_classification': 8760,
    }
    
    def __init__(self, db_path: str = 'data/cache.db'):
        """Initialize cache manager with SQLite database"""
        self.db_path = db_path
        
        # Create data directory if doesn't exist
        os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else 'data', exist_ok=True)
        
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database with schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Cache table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cache (
                key TEXT PRIMARY KEY,
                data_type TEXT NOT NULL,
                ticker TEXT,
                data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                access_count INTEGER DEFAULT 0,
                cost_saved REAL DEFAULT 0.0
            )
        ''')
        
        # Cost tracking table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_costs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                module TEXT NOT NULL,
                api_name TEXT NOT NULL,
                tokens_used INTEGER,
                cost REAL,
                cache_hit BOOLEAN DEFAULT 0
            )
        ''')
        
        # Quarterly earnings schedule
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS earnings_calendar (
                ticker TEXT PRIMARY KEY,
                last_earnings_date DATE,
                next_earnings_date DATE,
                fiscal_quarter TEXT,
                fiscal_year INTEGER
            )
        ''')
        
        # Data freshness monitor
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS freshness_monitor (
                ticker TEXT,
                data_type TEXT,
                last_checked TIMESTAMP,
                last_updated TIMESTAMP,
                needs_refresh BOOLEAN DEFAULT 0,
                PRIMARY KEY (ticker, data_type)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _generate_key(self, data_type: str, ticker: str = None, **kwargs) -> str:
        """Generate unique cache key"""
        key_parts = [data_type]
        if ticker:
            key_parts.append(ticker.upper())
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}:{v}")
        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def should_refresh(self, data_type: str, ticker: str = None) -> bool:
        """Determine if data should be refreshed based on freshness rules"""
        
        key = self._generate_key(data_type, ticker)
        
        # Get freshness rule (default to 24 hours if not specified)
        max_age_hours = self.FRESHNESS_RULES.get(data_type, 24)
        
        # If max_age is 0, always refresh (real-time data)
        if max_age_hours == 0:
            return True
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT created_at, expires_at FROM cache WHERE key = ?
        ''', (key,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return True  # No cached data, must refresh
        
        created_at = datetime.fromisoformat(result[0])
        age_hours = (datetime.now() - created_at).total_seconds() / 3600
        
        return age_hours >= max_age_hours
    
    def get(self, data_type: str, ticker: str = None, **kwargs) -> Optional[Dict]:
        """Get cached data if fresh, otherwise return None"""
        
        key = self._generate_key(data_type, ticker, **kwargs)
        
        if self.should_refresh(data_type, ticker):
            return None  # Data is stale or doesn't exist
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT data FROM cache WHERE key = ? AND expires_at > datetime('now')
        ''', (key,))
        
        result = cursor.fetchone()
        
        if result:
            # Update access tracking
            cursor.execute('''
                UPDATE cache 
                SET accessed_at = datetime('now'), access_count = access_count + 1
                WHERE key = ?
            ''', (key,))
            conn.commit()
            
            # Log cache hit
            self._log_cache_hit(data_type, ticker)
        
        conn.close()
        
        if result:
            return json.loads(result[0])
        return None
    
    def set(self, data_type: str, data: Dict, ticker: str = None, 
            cost: float = 0.0, **kwargs):
        """Store data in cache with automatic expiration"""
        
        key = self._generate_key(data_type, ticker, **kwargs)
        max_age_hours = self.FRESHNESS_RULES.get(data_type, 24)
        
        expires_at = datetime.now() + timedelta(hours=max_age_hours)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO cache 
            (key, data_type, ticker, data, expires_at, cost_saved)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (key, data_type, ticker, json.dumps(data), expires_at, cost))
        
        conn.commit()
        conn.close()
    
    def _log_cache_hit(self, data_type: str, ticker: str = None):
        """Log cache hit for cost tracking"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Estimate cost saved based on data type
        cost_saved = self._estimate_cost(data_type)
        
        cursor.execute('''
            INSERT INTO api_costs (module, api_name, cost, cache_hit)
            VALUES (?, ?, ?, 1)
        ''', (data_type, ticker or 'N/A', cost_saved))
        
        conn.commit()
        conn.close()
    
    def _estimate_cost(self, data_type: str) -> float:
        """Estimate cost saved by using cache"""
        cost_map = {
            'fed_rate': 0.001,  # FRED is free but time saved
            'inflation': 0.001,
            'treasury_yield': 0.001,
            'supplier_relationships': 0.17,  # Expensive AI analysis
            'customer_relationships': 0.17,
            'macro_trends': 0.06,
            'financial_statements': 0.02,
        }
        return cost_map.get(data_type, 0.01)
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total cached items
        cursor.execute('SELECT COUNT(*) FROM cache')
        total_items = cursor.fetchone()[0]
        
        # Fresh vs stale
        cursor.execute('''
            SELECT 
                COUNT(CASE WHEN expires_at > datetime('now') THEN 1 END) as fresh,
                COUNT(CASE WHEN expires_at <= datetime('now') THEN 1 END) as stale
            FROM cache
        ''')
        fresh, stale = cursor.fetchone()
        
        # Total cost saved
        cursor.execute('SELECT SUM(cost_saved) FROM cache')
        cost_saved = cursor.fetchone()[0] or 0.0
        
        # Cache hits today
        cursor.execute('''
            SELECT COUNT(*) FROM api_costs 
            WHERE cache_hit = 1 AND DATE(timestamp) = DATE('now')
        ''')
        hits_today = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_items': total_items,
            'fresh_items': fresh,
            'stale_items': stale,
            'cost_saved_total': round(cost_saved, 2),
            'cache_hits_today': hits_today,
            'hit_rate': round((fresh / total_items * 100) if total_items > 0 else 0, 1)
        }
    
    def update_earnings_schedule(self, ticker: str, last_date: str, 
                                 next_date: str, quarter: str, year: int):
        """Update earnings calendar for intelligent quarterly refresh"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO earnings_calendar
            (ticker, last_earnings_date, next_earnings_date, fiscal_quarter, fiscal_year)
            VALUES (?, ?, ?, ?, ?)
        ''', (ticker, last_date, next_date, quarter, year))
        
        conn.commit()
        conn.close()
    
    def needs_quarterly_refresh(self, ticker: str) -> bool:
        """Check if quarterly data needs refresh based on earnings calendar"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT last_earnings_date, next_earnings_date FROM earnings_calendar
            WHERE ticker = ?
        ''', (ticker,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return True  # No schedule found, needs refresh
        
        last_earnings = datetime.fromisoformat(result[0])
        days_since_earnings = (datetime.now() - last_earnings).days
        
        # Refresh if more than 5 days since earnings
        return days_since_earnings > 5
    
    def clear_stale(self):
        """Remove stale cache entries"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM cache WHERE expires_at < datetime('now')
        ''')
        
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        
        return deleted
    
    def force_refresh(self, data_type: str = None, ticker: str = None):
        """Force refresh of specific data type or ticker"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if data_type and ticker:
            key = self._generate_key(data_type, ticker)
            cursor.execute('DELETE FROM cache WHERE key = ?', (key,))
        elif data_type:
            cursor.execute('DELETE FROM cache WHERE data_type = ?', (data_type,))
        elif ticker:
            cursor.execute('DELETE FROM cache WHERE ticker = ?', (ticker,))
        
        conn.commit()
        conn.close()
