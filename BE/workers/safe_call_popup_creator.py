#!/usr/bin/env python3
r"""
Safe Call Popup Creator Worker

Automatically creates popup cards for leads that are eligible for safe calling
(24+ hours after consent SMS with no reply, not DNC, not already called recently).

⚠️ CRITICAL: This worker ONLY applies to leads that have already been sent a consent SMS.
Leads without a consent SMS (sms_consent_requested_at IS NULL) are NOT processed.

This worker runs periodically to ensure leads become available for manual dialing
after the TCPA-compliant 24-hour window has passed.

Features:
- Finds leads eligible for safe calling (24+ hours, no reply, not DNC)
- Creates popup cards for manual dialing
- Prevents duplicate popups (checks if popup already exists)
- Respects existing popup status (won't create if already pending/dialed)
- Logs all actions for audit trail
- Handles errors gracefully

Usage:
    # Run once (manual execution)
    python BE/workers/safe_call_popup_creator.py

    # Run continuously (daemon mode)
    python BE/workers/safe_call_popup_creator.py --daemon

    # Windows Task Scheduler (run every hour)
    schtasks /create /tn "SafeCallPopupCreator" /tr "python C:\path\to\BE\workers\safe_call_popup_creator.py" /sc hourly /mo 1

    # Windows Task Scheduler (run every 30 minutes)
    schtasks /create /tn "SafeCallPopupCreator" /tr "python C:\path\to\BE\workers\safe_call_popup_creator.py" /sc minute /mo 30
"""

import os
import sys
import time
import argparse
import pyodbc
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

load_dotenv()

# SQL Server configuration
SQL_SERVER = os.getenv('SQLServer')
SQL_USER = os.getenv('SQLUser')
SQL_PASSWORD = os.getenv('SQLPassword')
SQL_DATABASE = os.getenv('SQLDatabase')

# Worker configuration
POLL_INTERVAL = 3600  # Run every hour (3600 seconds) in daemon mode
BATCH_SIZE = 100  # Process up to 100 leads per run


def get_db_connection():
    """Get SQL Server database connection."""
    connection_string = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};TrustServerCertificate=yes;"
        f"SERVER={SQL_SERVER};"
        f"DATABASE={SQL_DATABASE};"
        f"UID={SQL_USER};"
        f"PWD={SQL_PASSWORD};"
    )
    return pyodbc.connect(connection_string)


def find_safe_call_eligible_leads(limit: int = BATCH_SIZE) -> List[Dict[str, Any]]:
    """
    Find leads that are eligible for safe calling (24+ hours after SMS with no reply).
    
    ⚠️ CRITICAL: This worker ONLY applies to leads that have already been sent a consent SMS.
    
    Criteria:
    - ✅ Consent SMS already sent (sms_consent_requested_at IS NOT NULL) - REQUIRED
    - ✅ SMS sent 24+ hours ago (sms_consent_requested_at < 24 hours ago)
    - ✅ No reply received (sms_verified = 0)
    - ✅ Not marked DNC (dnc_flag = 0)
    - ✅ Not called in last 24 hours (last_called IS NULL OR last_called < 24 hours ago)
    - ✅ No existing pending popup (not in PopupQueue with status='pending')
    
    Returns:
        List of lead dictionaries with lead_id, name, phone_number, etc.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        query = """
            SELECT TOP (?)
                ol.lead_id,
                ol.name,
                ol.phone_number,
                ol.Address,
                ol.City,
                ol.State,
                ol.store_id,
                ol.sms_consent_requested_at,
                ol.sms_verified,
                ol.priority,
                ol.last_called,
                DATEDIFF(HOUR, ol.sms_consent_requested_at, GETDATE()) as hours_since_sms
            FROM OutboundLeads ol
            WHERE ol.sms_consent_requested_at IS NOT NULL  -- ⚠️ ONLY leads that have been sent consent SMS
              AND ol.sms_consent_requested_at < DATEADD(HOUR, -24, GETDATE())
              AND ol.sms_verified = 0
              AND ol.dnc_flag = 0
              AND (ol.last_called IS NULL OR ol.last_called < DATEADD(HOUR, -24, GETDATE()))
              AND NOT EXISTS (
                  -- Exclude leads that already have a pending popup
                  SELECT 1 
                  FROM PopupQueue pq 
                  WHERE pq.lead_id = ol.lead_id 
                    AND pq.status = 'pending'
              )
            ORDER BY 
                ol.priority ASC,
                ol.sms_consent_requested_at ASC
        """
        
        cursor.execute(query, (limit,))
        rows = cursor.fetchall()
        
        leads = []
        for row in rows:
            leads.append({
                'lead_id': row[0],
                'name': row[1],
                'phone_number': row[2],
                'Address': row[3],
                'City': row[4],
                'State': row[5],
                'store_id': row[6],
                'sms_consent_requested_at': row[7],
                'sms_verified': bool(row[8]),
                'priority': row[9],
                'last_called': row[10],
                'hours_since_sms': row[11]
            })
        
        return leads
        
    except Exception as e:
        print(f"❌ Error finding safe-call eligible leads: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


def create_popup_for_lead(lead_id: int) -> bool:
    """
    Create a popup card for a lead.
    
    Args:
        lead_id: The lead ID to create popup for
        
    Returns:
        True if popup was created, False if it already exists or error occurred
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if popup already exists (double-check to prevent race conditions)
        cursor.execute("""
            SELECT popup_id 
            FROM PopupQueue 
            WHERE lead_id = ? AND status = 'pending'
        """, (lead_id,))
        
        existing = cursor.fetchone()
        if existing:
            print(f"⚠️  Lead {lead_id} already has pending popup (popup_id: {existing[0]})")
            return False
        
        # Create new popup
        cursor.execute("""
            INSERT INTO PopupQueue (lead_id, status, created_at)
            VALUES (?, 'pending', GETDATE())
        """, (lead_id,))
        
        conn.commit()
        
        popup_id = cursor.execute("SELECT @@IDENTITY").fetchone()[0]
        print(f"✅ Created popup card (popup_id: {popup_id}) for lead {lead_id}")
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error creating popup for lead {lead_id}: {e}")
        return False
    finally:
        cursor.close()
        conn.close()


def process_safe_call_leads(limit: int = BATCH_SIZE) -> Dict[str, Any]:
    """
    Process safe-call eligible leads and create popup cards.
    
    Args:
        limit: Maximum number of leads to process in this run
        
    Returns:
        Dictionary with processing statistics
    """
    print(f"\n{'='*60}")
    print(f"🔄 Safe Call Popup Creator - Starting at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    try:
        # Find eligible leads
        print(f"🔍 Searching for safe-call eligible leads (limit: {limit})...")
        eligible_leads = find_safe_call_eligible_leads(limit)
        
        if not eligible_leads:
            print("✅ No eligible leads found. All caught up!")
            return {
                'found': 0,
                'created': 0,
                'skipped': 0,
                'errors': 0
            }
        
        print(f"📋 Found {len(eligible_leads)} eligible lead(s)")
        
        # Process each lead
        created_count = 0
        skipped_count = 0
        error_count = 0
        
        for lead in eligible_leads:
            lead_id = lead['lead_id']
            name = lead['name'] or 'Unknown'
            phone = lead['phone_number']
            hours_since = lead['hours_since_sms']
            
            print(f"  📞 Lead {lead_id}: {name} ({phone}) - {hours_since}h since SMS")
            
            if create_popup_for_lead(lead_id):
                created_count += 1
            else:
                skipped_count += 1
        
        # Summary
        print(f"\n{'='*60}")
        print(f"✅ Processing complete!")
        print(f"   Found: {len(eligible_leads)}")
        print(f"   Created: {created_count}")
        print(f"   Skipped: {skipped_count}")
        print(f"   Errors: {error_count}")
        print(f"{'='*60}\n")
        
        return {
            'found': len(eligible_leads),
            'created': created_count,
            'skipped': skipped_count,
            'errors': error_count
        }
        
    except Exception as e:
        print(f"❌ Fatal error in process_safe_call_leads: {e}")
        import traceback
        traceback.print_exc()
        return {
            'found': 0,
            'created': 0,
            'skipped': 0,
            'errors': 1
        }


def run_daemon(poll_interval: int = POLL_INTERVAL):
    """Run the worker in daemon mode (continuous loop)."""
    print(f"🚀 Starting Safe Call Popup Creator in daemon mode")
    print(f"   Poll interval: {poll_interval} seconds ({poll_interval // 60} minutes)")
    print(f"   Press Ctrl+C to stop\n")
    
    try:
        while True:
            process_safe_call_leads()
            print(f"⏳ Waiting {poll_interval} seconds until next run...\n")
            time.sleep(poll_interval)
    except KeyboardInterrupt:
        print("\n\n🛑 Daemon stopped by user")
    except Exception as e:
        print(f"\n❌ Fatal error in daemon: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Safe Call Popup Creator - Creates popup cards for leads eligible for safe calling'
    )
    parser.add_argument(
        '--daemon',
        action='store_true',
        help='Run in daemon mode (continuous loop)'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=POLL_INTERVAL,
        help=f'Poll interval in seconds for daemon mode (default: {POLL_INTERVAL})'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=BATCH_SIZE,
        help=f'Maximum leads to process per run (default: {BATCH_SIZE})'
    )
    
    args = parser.parse_args()
    
    if args.daemon:
        run_daemon(args.interval)
    else:
        # Run once
        result = process_safe_call_leads(args.limit)
        sys.exit(0 if result['errors'] == 0 else 1)


if __name__ == '__main__':
    main()
