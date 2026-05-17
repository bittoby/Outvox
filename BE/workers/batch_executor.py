#!/usr/bin/env python3
"""
Batch Executor Worker (Milestone 15)

Automatically executes pending SMS batches on schedule.
This worker polls for batches with status='pending' and scheduled_at <= NOW(),
then executes them using SMSCampaignManager.execute_batch().

⚠️ CRITICAL: This worker ACTUALLY SENDS SMS messages via Twilio and incurs charges!

Usage:
    # Run once (manual execution)
    python BE/workers/batch_executor.py

    # Run continuously (daemon mode)
    python BE/workers/batch_executor.py --daemon

    # Windows Task Scheduler (run every minute)
    schtasks /create /tn "SMS_BatchExecutor" /tr "python C:\\path\\to\\BE\\workers\\batch_executor.py" /sc minute /mo 1

Features:
- Polls database every 30 seconds for pending batches
- Respects scheduled_at timestamp (won't execute early)
- Respects campaign status (paused campaigns are skipped)
- Handles errors gracefully (marks batches as failed)
- Logs all execution attempts for audit trail
- Prevents concurrent execution of same batch
"""

import os
import sys
import time
import asyncio
import argparse
import pyodbc
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.sms_campaign_manager import SMSCampaignManager

load_dotenv()

# SQL Server configuration
SQL_SERVER = os.getenv('SQLServer')
SQL_USER = os.getenv('SQLUser')
SQL_PASSWORD = os.getenv('SQLPassword')
SQL_DATABASE = os.getenv('SQLDatabase')

# Worker configuration
POLL_INTERVAL_SECONDS = 30  # Check for pending batches every 30 seconds
MAX_EXECUTION_RETRIES = 3  # Retry failed batches up to 3 times


class BatchExecutorWorker:
    """
    Worker that polls for pending SMS batches and executes them.
    
    Process:
    1. Query database for batches where:
       - status = 'pending'
       - scheduled_at <= NOW()
       - campaign.status != 'paused'
    2. For each batch:
       - Mark as 'executing' (prevents duplicate execution)
       - Call SMSCampaignManager.execute_batch(batch_id)
       - Update batch status based on result
    3. Sleep for POLL_INTERVAL_SECONDS
    4. Repeat
    """
    
    def __init__(self):
        """Initialize the batch executor worker."""
        self.connection_string = (
            f"DRIVER={{ODBC Driver 18 for SQL Server}};TrustServerCertificate=yes;"
            f"SERVER={SQL_SERVER};"
            f"DATABASE={SQL_DATABASE};"
            f"UID={SQL_USER};"
            f"PWD={SQL_PASSWORD}"
        )
        self.sms_manager = SMSCampaignManager()
        self.is_running = False
    
    def get_db_connection(self):
        """Get database connection."""
        return pyodbc.connect(self.connection_string)
    
    def get_pending_batches(self) -> List[Dict[str, Any]]:
        """
        Fetch pending batches that are ready to execute.
        
        Returns:
            List of batch dictionaries with details
        """
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT 
                    b.batch_id,
                    b.campaign_id,
                    b.batch_number,
                    b.target_count,
                    b.scheduled_at,
                    c.store_id,
                    s.name as store_name,
                    c.status as campaign_status
                FROM sms_batches b
                JOIN sms_campaigns c ON b.campaign_id = c.campaign_id
                JOIN stores s ON c.store_id = s.store_id
                WHERE b.status = 'pending'
                  AND b.scheduled_at <= GETDATE()
                  AND c.status NOT IN ('paused', 'cancelled', 'completed')
                ORDER BY b.scheduled_at ASC
            """)
            
            batches = []
            for row in cursor.fetchall():
                batches.append({
                    'batch_id': row[0],
                    'campaign_id': row[1],
                    'batch_number': row[2],
                    'target_count': row[3],
                    'scheduled_at': row[4],
                    'store_id': row[5],
                    'store_name': row[6],
                    'campaign_status': row[7]
                })
            
            return batches
        
        finally:
            cursor.close()
            conn.close()
    
    def check_campaign_completion(self, campaign_id: int) -> bool:
        """
        Check if all batches for a campaign are completed.
        If so, mark campaign as completed.
        
        Args:
            campaign_id: Campaign ID to check
        
        Returns:
            bool: True if campaign was just completed, False otherwise
        """
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Check if any batches are still pending or executing
            cursor.execute("""
                SELECT COUNT(*) as pending_count
                FROM sms_batches
                WHERE campaign_id = ?
                  AND status IN ('pending', 'executing')
            """, campaign_id)
            
            pending_count = cursor.fetchone()[0]
            
            if pending_count == 0:
                # All batches completed, mark campaign as completed
                cursor.execute("""
                    UPDATE sms_campaigns
                    SET 
                        status = 'completed',
                        completed_at = GETDATE()
                    WHERE campaign_id = ?
                      AND status NOT IN ('completed', 'cancelled')
                """, campaign_id)
                conn.commit()
                
                if cursor.rowcount > 0:
                    print(f"✅ Campaign {campaign_id} marked as completed (all batches finished)")
                    return True
            
            return False
        
        except Exception as e:
            print(f"⚠️  Error checking campaign completion: {e}")
            return False
        
        finally:
            cursor.close()
            conn.close()
    
    async def execute_batch(self, batch: Dict[str, Any]) -> bool:
        """
        Execute a single batch.
        
        Args:
            batch: Batch dictionary with details
        
        Returns:
            True if execution successful, False otherwise
        """
        batch_id = batch['batch_id']
        campaign_id = batch['campaign_id']
        
        try:
            # Check business hours (9AM-6PM) before execution
            now = datetime.now()
            current_hour = now.hour
            
            if current_hour < 9 or current_hour >= 18:
                print(f"\n⏰ Batch {batch_id} skipped - outside business hours (9AM-6PM)")
                print(f"   Current time: {now.strftime('%I:%M %p')}")
                print(f"   Will retry at next execution cycle")
                return False
            
            print(f"\n{'='*70}")
            print(f"[Batch Executor] Executing batch {batch_id}")
            print(f"   Campaign ID: {campaign_id}")
            print(f"   Batch Number: {batch['batch_number']}")
            print(f"   Store: {batch['store_name']} (ID: {batch['store_id']})")
            print(f"   Target Count: {batch['target_count']}")
            print(f"   Scheduled At: {batch['scheduled_at']}")
            print(f"{'='*70}")
            
            # Execute batch using SMSCampaignManager
            result = await self.sms_manager.execute_batch(batch_id)
            
            print(f"\n✅ Batch {batch_id} execution completed successfully")
            print(f"   SMS Sent: {result['actual_sent']}/{result['target_count']}")
            print(f"   Failed: {result['failed_count']}")
            print(f"   Duration: {result['duration_seconds']} seconds")
            
            # Check if campaign is now complete
            campaign_completed = self.check_campaign_completion(campaign_id)
            
            # Broadcast campaign update event for UI real-time updates
            try:
                from services.websocket_service import broadcast_event_sync, EventType
                broadcast_event_sync(
                    EventType.CAMPAIGN_UPDATED,
                    {
                        "campaign_id": campaign_id,
                        "batch_id": batch_id,
                        "batch_status": "completed",
                        "sent_count": result['actual_sent'],
                        "target_count": result['target_count'],
                        "failed_count": result['failed_count'],
                        "campaign_completed": campaign_completed
                    }
                )
            except Exception as e:
                print(f"[Batch Executor] WARNING: Failed to broadcast campaign update: {e}")
            
            return True
        
        except Exception as e:
            print(f"\n❌ Batch {batch_id} execution failed: {e}")
            return False
    
    async def run_once(self):
        """
        Run one iteration of the worker (check and execute pending batches).
        """
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Checking for pending batches...")
        
        # Fetch pending batches
        pending_batches = self.get_pending_batches()
        
        if not pending_batches:
            print(f"   No pending batches ready for execution")
            return
        
        print(f"   Found {len(pending_batches)} pending batch(es) ready for execution")
        
        # Execute each batch
        for batch in pending_batches:
            await self.execute_batch(batch)
            
            # Small delay between batches to avoid overwhelming the system
            await asyncio.sleep(2)
    
    async def run_daemon(self):
        """
        Run worker continuously (daemon mode).
        """
        self.is_running = True
        
        print(f"\n{'='*70}")
        print(f"Batch Executor Worker - Daemon Mode")
        print(f"{'='*70}")
        print(f"Poll interval: {POLL_INTERVAL_SECONDS} seconds")
        print(f"Database: {SQL_DATABASE}")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}\n")
        print(f"Press Ctrl+C to stop\n")
        
        try:
            while self.is_running:
                try:
                    await self.run_once()
                except Exception as e:
                    print(f"\n❌ Error in worker iteration: {e}")
                
                # Sleep for poll interval
                await asyncio.sleep(POLL_INTERVAL_SECONDS)
        
        except KeyboardInterrupt:
            print(f"\n\n{'='*70}")
            print(f"Batch Executor Worker shutting down...")
            print(f"{'='*70}\n")
            self.is_running = False
    
    def stop(self):
        """Stop the worker gracefully."""
        self.is_running = False


async def main():
    """Main entry point for batch executor worker."""
    parser = argparse.ArgumentParser(description='SMS Batch Executor Worker')
    parser.add_argument(
        '--daemon',
        action='store_true',
        help='Run in daemon mode (continuous polling)'
    )
    
    args = parser.parse_args()
    
    worker = BatchExecutorWorker()
    
    if args.daemon:
        # Run continuously
        await worker.run_daemon()
    else:
        # Run once
        await worker.run_once()


if __name__ == "__main__":
    asyncio.run(main())

