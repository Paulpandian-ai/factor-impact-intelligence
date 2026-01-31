"""
Autonomous Background Scheduler
Runs agent monitoring cycles continuously in the background

This enables true autonomous operation:
- Runs 24/7 without user input
- Monitors watchlist continuously
- Takes actions autonomously
- Learns from outcomes
"""

import schedule
import time
import threading
from datetime import datetime
from agent_orchestrator import AgentOrchestrator

class AutonomousScheduler:
    """
    Background scheduler for autonomous agent operation
    
    This is what makes the system truly autonomous:
    - Runs monitoring cycles on a schedule
    - No user interaction required
    - Operates continuously
    """
    
    def __init__(self, anthropic_api_key: str):
        """Initialize scheduler"""
        self.orchestrator = AgentOrchestrator(anthropic_api_key)
        self.running = False
        self.thread = None
        
    def start(self):
        """Start autonomous operation"""
        if self.running:
            print("⚠️ Scheduler already running")
            return
        
        print("🚀 Starting Autonomous AI Agent System...")
        self.running = True
        
        # Schedule monitoring cycles
        # Run every hour for main monitoring
        schedule.every().hour.do(self.run_monitoring_cycle)
        
        # Run every 15 minutes for quick checks
        schedule.every(15).minutes.do(self.run_quick_check)
        
        # Run daily for strategic planning
        schedule.every().day.at("09:00").do(self.run_daily_planning)
        
        # Run immediately first time
        self.run_monitoring_cycle()
        
        # Start background thread
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
        
        print("✅ Autonomous agent system is now running in background!")
        print("   - Full monitoring: Every hour")
        print("   - Quick checks: Every 15 minutes")
        print("   - Strategic planning: Daily at 9 AM")
    
    def _run_scheduler(self):
        """Run schedule loop in background"""
        while self.running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def run_monitoring_cycle(self):
        """Run full autonomous monitoring cycle"""
        print(f"\n{'='*60}")
        print(f"🤖 AUTONOMOUS MONITORING CYCLE - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"{'='*60}")
        
        try:
            result = self.orchestrator.autonomous_monitoring_loop()
            
            print(f"\n✅ Cycle Complete:")
            print(f"   Actions Decided: {result['actions_decided']}")
            print(f"   Actions Executed: {result['actions_executed']}")
            print(f"   Insights Generated: {result['insights_generated']}")
            print(f"   Active Alerts: {result['active_alerts']}")
            
        except Exception as e:
            print(f"❌ Monitoring cycle failed: {e}")
    
    def run_quick_check(self):
        """Run quick check of watchlist"""
        print(f"\n⚡ Quick Check - {datetime.now().strftime('%H:%M')}")
        
        try:
            # Check for any critical alerts or changes
            alerts = self.orchestrator._get_active_alerts()
            critical = [a for a in alerts if a['severity'] in ['CRITICAL', 'HIGH']]
            
            if critical:
                print(f"   🚨 {len(critical)} critical alerts - triggering investigation")
                
                for alert in critical[:3]:
                    self.orchestrator.schedule_action(
                        action_type='investigate_alert',
                        ticker=alert['ticker'],
                        priority=5,
                        reason=alert['message'],
                        scheduled_for='immediate'
                    )
                
                # Execute immediately
                self.orchestrator.execute_pending_actions()
            else:
                print(f"   ✅ No critical alerts")
                
        except Exception as e:
            print(f"   ❌ Quick check failed: {e}")
    
    def run_daily_planning(self):
        """Run daily strategic planning"""
        print(f"\n📅 DAILY STRATEGIC PLANNING - {datetime.now().strftime('%Y-%m-%d')}")
        
        try:
            # Review watchlist strategy
            watchlist = self.orchestrator._get_watchlist()
            
            print(f"   📊 Current watchlist: {len(watchlist)} tickers")
            
            # Trigger strategic review for each ticker
            for item in watchlist:
                self.orchestrator.schedule_action(
                    action_type='monitor_changes',
                    ticker=item['ticker'],
                    priority=2,
                    reason='Daily strategic review',
                    scheduled_for='immediate'
                )
            
            print(f"   ✅ Scheduled strategic review for {len(watchlist)} tickers")
            
        except Exception as e:
            print(f"   ❌ Daily planning failed: {e}")
    
    def stop(self):
        """Stop autonomous operation"""
        print("\n🛑 Stopping autonomous agent system...")
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print("✅ Stopped")
    
    def add_ticker_to_watchlist(self, ticker: str, importance: int = 3):
        """Add ticker to autonomous monitoring"""
        self.orchestrator.add_to_watchlist(ticker, importance=importance)
    
    def get_status(self) -> dict:
        """Get current agent status"""
        return self.orchestrator.get_agent_status()


# Example usage for testing
if __name__ == "__main__":
    import os
    
    # Get API key from environment
    api_key = os.getenv('ANTHROPIC_API_KEY')
    
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not found in environment")
        exit(1)
    
    # Initialize scheduler
    scheduler = AutonomousScheduler(api_key)
    
    # Add some tickers to watchlist
    print("\n📋 Adding tickers to watchlist...")
    scheduler.add_ticker_to_watchlist('NVDA', importance=5)  # High importance
    scheduler.add_ticker_to_watchlist('AMD', importance=4)
    scheduler.add_ticker_to_watchlist('TSLA', importance=3)
    
    # Start autonomous operation
    scheduler.start()
    
    try:
        # Run for 1 hour (for testing)
        print("\n⏰ Running for 1 hour... (Press Ctrl+C to stop earlier)")
        time.sleep(3600)
    except KeyboardInterrupt:
        print("\n⏹️ Interrupted by user")
    finally:
        scheduler.stop()
