"""
Sentinel Engine - The Intelligence Layer
Learns, stores insights, monitors for changes, updates incrementally
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from cache_manager import DataCacheManager

class SentinelEngine:
    """
    Sentinel Intelligence System
    
    Capabilities:
    1. Learn - Store and index all analysis results
    2. Monitor - Track what changed and why
    3. Alert - Notify when significant changes occur
    4. Optimize - Recommend what data needs refresh
    5. Predict - Anticipate when updates are needed
    """
    
    def __init__(self, db_path: str = 'data/sentinel.db'):
        """Initialize Sentinel engine"""
        self.db_path = db_path
        self.cache = DataCacheManager()
        self._init_database()
    
    def _init_database(self):
        """Initialize intelligence database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Analysis history - learn from past analyses
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analysis_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                combined_score REAL,
                signal TEXT,
                monetary_score REAL,
                company_score REAL,
                supplier_score REAL,
                customer_score REAL,
                macro_score REAL,
                cost REAL,
                key_insights TEXT
            )
        ''')
        
        # Change detection - monitor what changed
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS change_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                change_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                module TEXT NOT NULL,
                field TEXT NOT NULL,
                old_value TEXT,
                new_value TEXT,
                magnitude REAL,
                significance TEXT
            )
        ''')
        
        # Learned insights - remember important patterns
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS learned_insights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                insight_type TEXT NOT NULL,
                insight TEXT NOT NULL,
                confidence REAL,
                learned_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_validated TIMESTAMP,
                validation_count INTEGER DEFAULT 0,
                still_valid BOOLEAN DEFAULT 1
            )
        ''')
        
        # Alert rules - track what to watch
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alert_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                rule_type TEXT NOT NULL,
                threshold REAL,
                last_triggered TIMESTAMP,
                trigger_count INTEGER DEFAULT 0,
                active BOOLEAN DEFAULT 1
            )
        ''')
        
        # Supplier/Customer tracking - remember relationships
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS relationships (
                ticker TEXT NOT NULL,
                related_entity TEXT NOT NULL,
                relationship_type TEXT NOT NULL,
                importance_score REAL,
                discovered_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                still_active BOOLEAN DEFAULT 1,
                PRIMARY KEY (ticker, related_entity, relationship_type)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def learn_from_analysis(self, ticker: str, results: Dict):
        """
        Learn from analysis results
        Store insights, detect changes, update knowledge base
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Store analysis history
        cursor.execute('''
            INSERT INTO analysis_history 
            (ticker, combined_score, signal, monetary_score, company_score, 
             supplier_score, customer_score, macro_score, cost, key_insights)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            ticker,
            results.get('combined_score'),
            results.get('combined_signal'),
            results.get('monetary', {}).get('score'),
            results.get('company', {}).get('score'),
            results.get('suppliers', {}).get('score'),
            results.get('customers', {}).get('score'),
            results.get('macro', {}).get('score'),
            results.get('total_cost', 0.0),
            json.dumps(results.get('key_insights', []))
        ))
        
        # Detect changes from previous analysis
        changes = self._detect_changes(ticker, results)
        for change in changes:
            cursor.execute('''
                INSERT INTO change_log 
                (ticker, module, field, old_value, new_value, magnitude, significance)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', change)
        
        # Learn new insights
        insights = self._extract_insights(ticker, results)
        for insight in insights:
            cursor.execute('''
                INSERT INTO learned_insights 
                (ticker, insight_type, insight, confidence)
                VALUES (?, ?, ?, ?)
            ''', insight)
        
        # Update relationships
        if 'suppliers' in results:
            self._update_relationships(
                cursor, ticker, 
                results['suppliers'].get('suppliers', []), 
                'supplier'
            )
        
        if 'customers' in results:
            self._update_relationships(
                cursor, ticker, 
                results['customers'].get('customers', []), 
                'customer'
            )
        
        conn.commit()
        conn.close()
    
    def _detect_changes(self, ticker: str, current: Dict) -> List[tuple]:
        """Detect what changed since last analysis"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get most recent previous analysis
        cursor.execute('''
            SELECT combined_score, monetary_score, company_score, 
                   supplier_score, customer_score, macro_score
            FROM analysis_history 
            WHERE ticker = ? 
            ORDER BY analysis_date DESC 
            LIMIT 1 OFFSET 1
        ''', (ticker,))
        
        previous = cursor.fetchone()
        conn.close()
        
        if not previous:
            return []  # No previous analysis to compare
        
        changes = []
        
        # Compare scores
        score_fields = [
            ('combined_score', previous[0], current.get('combined_score')),
            ('monetary_score', previous[1], current.get('monetary', {}).get('score')),
            ('company_score', previous[2], current.get('company', {}).get('score')),
            ('supplier_score', previous[3], current.get('suppliers', {}).get('score')),
            ('customer_score', previous[4], current.get('customers', {}).get('score')),
            ('macro_score', previous[5], current.get('macro', {}).get('score')),
        ]
        
        for field, old, new in score_fields:
            if old is not None and new is not None:
                magnitude = abs(new - old)
                if magnitude >= 0.5:  # Significant change
                    significance = 'HIGH' if magnitude >= 1.5 else 'MEDIUM'
                    changes.append((
                        ticker, 
                        field.replace('_score', ''), 
                        field, 
                        str(old), 
                        str(new), 
                        magnitude, 
                        significance
                    ))
        
        return changes
    
    def _extract_insights(self, ticker: str, results: Dict) -> List[tuple]:
        """Extract and store new insights"""
        insights = []
        
        # High supplier risk insight
        if results.get('suppliers', {}).get('score', 10) < 6.0:
            insights.append((
                ticker,
                'supply_chain_risk',
                f"High supply chain risk detected (score: {results['suppliers']['score']})",
                0.8
            ))
        
        # Strong customer demand insight
        if results.get('customers', {}).get('score', 0) >= 8.0:
            insights.append((
                ticker,
                'demand_strength',
                f"Strong customer demand (score: {results['customers']['score']})",
                0.9
            ))
        
        # Monetary headwinds insight
        if results.get('monetary', {}).get('score', 10) < 5.0:
            insights.append((
                ticker,
                'monetary_headwind',
                f"Monetary headwinds present (score: {results['monetary']['score']})",
                0.7
            ))
        
        return insights
    
    def _update_relationships(self, cursor, ticker: str, entities: List[Dict], rel_type: str):
        """Update supplier/customer relationships"""
        for entity in entities:
            cursor.execute('''
                INSERT OR REPLACE INTO relationships 
                (ticker, related_entity, relationship_type, importance_score, last_updated)
                VALUES (?, ?, ?, ?, datetime('now'))
            ''', (
                ticker,
                entity.get('name', 'Unknown'),
                rel_type,
                abs(entity.get('score', 0))
            ))
    
    def get_historical_trend(self, ticker: str, days: int = 90) -> Dict:
        """Get historical score trends"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff = datetime.now() - timedelta(days=days)
        
        cursor.execute('''
            SELECT analysis_date, combined_score, signal,
                   monetary_score, company_score, supplier_score, 
                   customer_score, macro_score
            FROM analysis_history
            WHERE ticker = ? AND analysis_date > ?
            ORDER BY analysis_date ASC
        ''', (ticker, cutoff))
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return {'trend': 'no_data', 'history': []}
        
        history = []
        for row in rows:
            history.append({
                'date': row[0],
                'score': row[1],
                'signal': row[2],
                'modules': {
                    'monetary': row[3],
                    'company': row[4],
                    'supplier': row[5],
                    'customer': row[6],
                    'macro': row[7]
                }
            })
        
        # Calculate trend
        if len(history) >= 2:
            first_score = history[0]['score']
            last_score = history[-1]['score']
            
            if last_score > first_score + 1.0:
                trend = 'improving'
            elif last_score < first_score - 1.0:
                trend = 'declining'
            else:
                trend = 'stable'
        else:
            trend = 'insufficient_data'
        
        return {
            'trend': trend,
            'history': history,
            'analyses_count': len(history)
        }
    
    def get_recent_changes(self, ticker: str, days: int = 30) -> List[Dict]:
        """Get recent significant changes"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff = datetime.now() - timedelta(days=days)
        
        cursor.execute('''
            SELECT change_date, module, field, old_value, new_value, 
                   magnitude, significance
            FROM change_log
            WHERE ticker = ? AND change_date > ? AND significance IN ('HIGH', 'MEDIUM')
            ORDER BY change_date DESC
            LIMIT 20
        ''', (ticker, cutoff))
        
        rows = cursor.fetchall()
        conn.close()
        
        changes = []
        for row in rows:
            changes.append({
                'date': row[0],
                'module': row[1],
                'field': row[2],
                'from': row[3],
                'to': row[4],
                'magnitude': row[5],
                'significance': row[6]
            })
        
        return changes
    
    def get_learned_insights(self, ticker: str, still_valid_only: bool = True) -> List[Dict]:
        """Get learned insights about a ticker"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = '''
            SELECT insight_type, insight, confidence, learned_date, 
                   validation_count, still_valid
            FROM learned_insights
            WHERE ticker = ?
        '''
        
        if still_valid_only:
            query += ' AND still_valid = 1'
        
        query += ' ORDER BY confidence DESC, learned_date DESC'
        
        cursor.execute(query, (ticker,))
        rows = cursor.fetchall()
        conn.close()
        
        insights = []
        for row in rows:
            insights.append({
                'type': row[0],
                'insight': row[1],
                'confidence': row[2],
                'learned_date': row[3],
                'validation_count': row[4],
                'still_valid': bool(row[5])
            })
        
        return insights
    
    def get_relationships(self, ticker: str, rel_type: str = None) -> List[Dict]:
        """Get supplier/customer relationships"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if rel_type:
            cursor.execute('''
                SELECT related_entity, relationship_type, importance_score, 
                       discovered_date, last_updated, still_active
                FROM relationships
                WHERE ticker = ? AND relationship_type = ? AND still_active = 1
                ORDER BY importance_score DESC
            ''', (ticker, rel_type))
        else:
            cursor.execute('''
                SELECT related_entity, relationship_type, importance_score, 
                       discovered_date, last_updated, still_active
                FROM relationships
                WHERE ticker = ? AND still_active = 1
                ORDER BY importance_score DESC
            ''', (ticker,))
        
        rows = cursor.fetchall()
        conn.close()
        
        relationships = []
        for row in rows:
            relationships.append({
                'entity': row[0],
                'type': row[1],
                'importance': row[2],
                'discovered': row[3],
                'updated': row[4],
                'active': bool(row[5])
            })
        
        return relationships
    
    def recommend_refresh(self, ticker: str) -> Dict:
        """Recommend what data needs refresh"""
        recommendations = {
            'urgent': [],
            'recommended': [],
            'optional': []
        }
        
        # Check last analysis date
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT analysis_date FROM analysis_history
            WHERE ticker = ?
            ORDER BY analysis_date DESC
            LIMIT 1
        ''', (ticker,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            recommendations['urgent'].append({
                'module': 'all',
                'reason': 'No previous analysis found'
            })
            return recommendations
        
        last_analysis = datetime.fromisoformat(result[0])
        days_since = (datetime.now() - last_analysis).days
        
        # Recommend based on time elapsed
        if days_since > 90:
            recommendations['urgent'].append({
                'module': 'company_financials',
                'reason': f'Last analysis {days_since} days ago - likely new quarterly data'
            })
            recommendations['urgent'].append({
                'module': 'suppliers',
                'reason': 'Quarterly refresh needed'
            })
            recommendations['urgent'].append({
                'module': 'customers',
                'reason': 'Quarterly refresh needed'
            })
        
        if days_since > 7:
            recommendations['recommended'].append({
                'module': 'macro_factors',
                'reason': 'Weekly refresh recommended'
            })
        
        if days_since > 1:
            recommendations['optional'].append({
                'module': 'monetary',
                'reason': 'Daily data may have updated'
            })
        
        return recommendations
    
    def get_sentinel_report(self, ticker: str) -> Dict:
        """Generate comprehensive sentinel report"""
        return {
            'ticker': ticker,
            'historical_trend': self.get_historical_trend(ticker),
            'recent_changes': self.get_recent_changes(ticker),
            'learned_insights': self.get_learned_insights(ticker),
            'relationships': {
                'suppliers': self.get_relationships(ticker, 'supplier'),
                'customers': self.get_relationships(ticker, 'customer')
            },
            'refresh_recommendations': self.recommend_refresh(ticker),
            'cache_stats': self.cache.get_stats()
        }
