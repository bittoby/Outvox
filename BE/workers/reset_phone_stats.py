#!/usr/bin/env python3
"""
Phone Stats Reset Worker
Resets hourly and daily counters for phone numbers to prevent exhaustion.

This script should be scheduled to run:
- Hourly: Every hour to reset hourly counters (SMS/call hourly limits)
- Daily: Once per day (e.g., midnight) to reset daily counters

Scheduling Options:
1. Windows Task Scheduler (Recommended for Windows)
2. cron (Linux/Mac)
3. Python scheduler like APScheduler (if running as daemon)

Usage:
    python BE/workers/reset_phone_stats.py hourly   # Reset hourly counters
    python BE/workers/reset_phone_stats.py daily    # Reset daily counters
    python BE/workers/reset_phone_stats.py both     # Reset both (for manual testing)
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.phone_pool_manager import PhoneNumberPoolManager


def reset_hourly():
    """Reset hourly counters for all phone numbers."""
    print(f"[{datetime.now().isoformat()}] Starting hourly phone stats reset...")
    
    try:
        manager = PhoneNumberPoolManager()
        rows_reset = manager.reset_hourly_stats()
        
        print(f"✅ Hourly reset completed: {rows_reset} phone numbers reset")
        print(f"   - hourly_sms_count set to 0")
        print(f"   - hourly_call_count set to 0")
        print(f"   - last_hourly_reset set to NOW()")
        
        return rows_reset
    
    except Exception as e:
        print(f"❌ Hourly reset failed: {e}")
        return 0


def reset_daily():
    """Reset daily counters for all phone numbers."""
    print(f"[{datetime.now().isoformat()}] Starting daily phone stats reset...")
    
    try:
        manager = PhoneNumberPoolManager()
        rows_reset = manager.reset_daily_stats()
        
        print(f"✅ Daily reset completed: {rows_reset} phone numbers reset")
        print(f"   - daily_sms_count set to 0")
        print(f"   - daily_call_count set to 0")
        print(f"   - hourly_sms_count set to 0")
        print(f"   - hourly_call_count set to 0")
        print(f"   - last_hourly_reset set to NOW()")
        
        return rows_reset
    
    except Exception as e:
        print(f"❌ Daily reset failed: {e}")
        return 0


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python reset_phone_stats.py [hourly|daily|both]")
        print("")
        print("Options:")
        print("  hourly  - Reset hourly counters (run every hour)")
        print("  daily   - Reset daily counters (run once per day)")
        print("  both    - Reset both hourly and daily (for testing)")
        print("")
        print("Examples:")
        print("  python BE/workers/reset_phone_stats.py hourly")
        print("  python BE/workers/reset_phone_stats.py daily")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    print("=" * 70)
    print("Phone Stats Reset Worker")
    print("=" * 70)
    
    if command == "hourly":
        reset_hourly()
    
    elif command == "daily":
        reset_daily()
    
    elif command == "both":
        print("Running both hourly and daily resets...\n")
        reset_hourly()
        print("")
        reset_daily()
    
    else:
        print(f"❌ Unknown command: {command}")
        print("Valid commands: hourly, daily, both")
        sys.exit(1)
    
    print("=" * 70)
    print(f"Reset completed at {datetime.now().isoformat()}")
    print("=" * 70)


if __name__ == "__main__":
    main()

