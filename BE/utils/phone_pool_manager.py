#!/usr/bin/env python3
"""
Phone Number Pool Manager
Implements LRU phone number selection with rate limit tracking for SMS and calls.

Key Features:
- LRU (Least Recently Used) selection: picks numbers that haven't been used recently
- Rate limit enforcement: hourly SMS < 25, daily SMS < 50, last batch > 20 min
- Store-based filtering: only returns numbers assigned to specific stores
- Usage type support: different limits for SMS vs. calls
- Safe counter management: atomic updates to prevent race conditions

Rate Limits:
- SMS: Max 25/hour, 50/day, 20 min cooldown between batches
- Calls: Max 15/hour, 30/day, 1 min cooldown between calls
"""

import os
import sys
import pyodbc
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Literal
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

load_dotenv()

# SQL Server configuration
SQL_SERVER = os.getenv('SQLServer')
SQL_USER = os.getenv('SQLUser')
SQL_PASSWORD = os.getenv('SQLPassword')
SQL_DATABASE = os.getenv('SQLDatabase')


class PhoneNumberPoolManager:
    """
    Manages phone number pool with LRU selection and rate limiting.
    
    Usage:
        manager = PhoneNumberPoolManager()
        
        # Get next available number for SMS
        number = manager.get_next_available_number(store_id=1, usage_type='sms')
        if number:
            # Send SMS...
            manager.increment_sms_counters(number['number_id'])
        
        # Get next available number for calls
        number = manager.get_next_available_number(store_id=1, usage_type='call')
        if number:
            # Make call...
            manager.increment_call_counters(number['number_id'])
    """
    
    # Rate limit constants
    SMS_HOURLY_LIMIT = 25
    SMS_DAILY_LIMIT = 50
    SMS_BATCH_COOLDOWN_MINUTES = 20
    
    CALL_HOURLY_LIMIT = 15
    CALL_DAILY_LIMIT = 30  # Per phone number: up to 30 calls per day
    CALL_COOLDOWN_MINUTES = 1
    
    def __init__(self):
        """Initialize the phone pool manager."""
        self.connection_string = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={SQL_SERVER};"
            f"DATABASE={SQL_DATABASE};"
            f"UID={SQL_USER};"
            f"PWD={SQL_PASSWORD}"
        )
    
    def get_db_connection(self):
        """Get database connection."""
        return pyodbc.connect(self.connection_string)
    
    def get_next_available_number(
        self, 
        store_id: int, 
        usage_type: Literal['sms', 'call'] = 'sms'
    ) -> Optional[Dict[str, Any]]:
        """
        Get the next available phone number using LRU selection.
        
        Selection Criteria (all must be met):
        - Number must be active (is_active=1)
        - Number must be assigned to the specified store (or store_id NULL for shared numbers)
        - Hourly limit not exceeded (SMS: <25, Call: <15)
        - Daily limit not exceeded (SMS: <50, Call: <30)
        - Cooldown period passed (SMS: >20 min, Call: >1 min since last use)
        
        LRU Logic:
        - Prioritizes numbers with oldest last_batch_sent_at (for SMS) or last_call_time (for calls)
        - NULL timestamps are treated as "never used" and prioritized first
        
        Args:
            store_id: Store ID to filter numbers (required)
            usage_type: 'sms' or 'call' to apply appropriate rate limits
        
        Returns:
            Dict with number details if available, None if all numbers exhausted
            {
                'number_id': int,
                'phone_number': str,
                'store_id': int,
                'hourly_sms_count': int,
                'daily_sms_count': int,
                'hourly_call_count': int,
                'last_batch_sent_at': datetime or None,
                'last_call_time': datetime or None
            }
        """
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            if usage_type == 'sms':
                # SMS rate limits
                query = """
                    SELECT TOP 1 
                        number_id,
                        phone_number,
                        store_id,
                        hourly_sms_count,
                        daily_sms_count,
                        hourly_call_count,
                        last_batch_sent_at,
                        last_call_time,
                        last_hourly_reset
                    FROM TwilioNumbers
                    WHERE is_active = 1
                      AND (store_id = ? OR store_id IS NULL)
                      AND (hourly_sms_count < ? OR hourly_sms_count IS NULL)
                      AND (daily_sms_count < ? OR daily_sms_count IS NULL)
                      AND (
                          last_batch_sent_at IS NULL 
                          OR last_batch_sent_at < DATEADD(MINUTE, -?, GETDATE())
                      )
                    ORDER BY 
                        CASE WHEN last_batch_sent_at IS NULL THEN 0 ELSE 1 END,  -- NULL first (never used)
                        last_batch_sent_at ASC  -- Then oldest used (LRU)
                """
                cursor.execute(
                    query, 
                    store_id, 
                    self.SMS_HOURLY_LIMIT, 
                    self.SMS_DAILY_LIMIT, 
                    self.SMS_BATCH_COOLDOWN_MINUTES
                )
            
            elif usage_type == 'call':
                # Call rate limits
                query = """
                    SELECT TOP 1 
                        number_id,
                        phone_number,
                        store_id,
                        hourly_sms_count,
                        daily_sms_count,
                        hourly_call_count,
                        last_batch_sent_at,
                        last_call_time,
                        last_hourly_reset
                    FROM TwilioNumbers
                    WHERE is_active = 1
                      AND (store_id = ? OR store_id IS NULL)
                      AND (hourly_call_count < ? OR hourly_call_count IS NULL)
                      AND (daily_call_count < ? OR daily_call_count IS NULL)
                      AND (
                          last_call_time IS NULL 
                          OR last_call_time < DATEADD(MINUTE, -?, GETDATE())
                      )
                    ORDER BY 
                        CASE WHEN last_call_time IS NULL THEN 0 ELSE 1 END,  -- NULL first (never used)
                        last_call_time ASC  -- Then oldest used (LRU)
                """
                cursor.execute(
                    query, 
                    store_id, 
                    self.CALL_HOURLY_LIMIT, 
                    self.CALL_DAILY_LIMIT, 
                    self.CALL_COOLDOWN_MINUTES
                )
            else:
                raise ValueError(f"Invalid usage_type: {usage_type}. Must be 'sms' or 'call'")
            
            row = cursor.fetchone()
            
            if row:
                return {
                    'number_id': row[0],
                    'phone_number': row[1],
                    'store_id': row[2],
                    'hourly_sms_count': row[3] or 0,
                    'daily_sms_count': row[4] or 0,
                    'hourly_call_count': row[5] or 0,
                    'last_batch_sent_at': row[6],
                    'last_call_time': row[7],
                    'last_hourly_reset': row[8]
                }
            else:
                # No available numbers - all are over limits or on cooldown
                return None
        
        finally:
            cursor.close()
            conn.close()
    
    def increment_sms_counters(self, number_id: int) -> bool:
        """
        Increment SMS counters for a phone number after sending SMS.
        
        Updates:
        - hourly_sms_count += 1
        - daily_sms_count += 1
        - last_batch_sent_at = NOW()
        
        Args:
            number_id: The number_id from TwilioNumbers table
        
        Returns:
            True if successful, False otherwise
        """
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE TwilioNumbers
                SET 
                    hourly_sms_count = ISNULL(hourly_sms_count, 0) + 1,
                    daily_sms_count = ISNULL(daily_sms_count, 0) + 1,
                    last_batch_sent_at = GETDATE()
                WHERE number_id = ?
            """, number_id)
            
            conn.commit()
            
            # Verify update
            if cursor.rowcount > 0:
                return True
            else:
                print(f"⚠️  Warning: No rows updated for number_id={number_id}")
                return False
        
        except Exception as e:
            conn.rollback()
            print(f"❌ Error incrementing SMS counters: {e}")
            return False
        
        finally:
            cursor.close()
            conn.close()
    
    def increment_call_counters(self, number_id: int) -> bool:
        """
        Increment call counters for a phone number after making a call.
        
        Updates:
        - hourly_call_count += 1
        - daily_call_count += 1
        - last_call_time = NOW()
        - total_calls_made += 1 (for historical tracking)
        
        Args:
            number_id: The number_id from TwilioNumbers table
        
        Returns:
            True if successful, False otherwise
        """
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE TwilioNumbers
                SET 
                    hourly_call_count = ISNULL(hourly_call_count, 0) + 1,
                    daily_call_count = ISNULL(daily_call_count, 0) + 1,
                    last_call_time = GETDATE(),
                    total_calls_made = ISNULL(total_calls_made, 0) + 1
                WHERE number_id = ?
            """, number_id)
            
            conn.commit()
            
            # Verify update
            if cursor.rowcount > 0:
                return True
            else:
                print(f"⚠️  Warning: No rows updated for number_id={number_id}")
                return False
        
        except Exception as e:
            conn.rollback()
            print(f"❌ Error incrementing call counters: {e}")
            return False
        
        finally:
            cursor.close()
            conn.close()
    
    def get_number_status(self, number_id: int) -> Optional[Dict[str, Any]]:
        """
        Get current status and counters for a phone number.
        
        Useful for debugging and monitoring.
        
        Args:
            number_id: The number_id from TwilioNumbers table
        
        Returns:
            Dict with number status, or None if not found
        """
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT 
                    number_id,
                    phone_number,
                    store_id,
                    hourly_sms_count,
                    daily_sms_count,
                    hourly_call_count,
                    daily_call_count,
                    last_batch_sent_at,
                    last_call_time,
                    last_hourly_reset,
                    last_reset_date,
                    is_active,
                    total_calls_made
                FROM TwilioNumbers
                WHERE number_id = ?
            """, number_id)
            
            row = cursor.fetchone()
            
            if row:
                return {
                    'number_id': row[0],
                    'phone_number': row[1],
                    'store_id': row[2],
                    'hourly_sms_count': row[3] or 0,
                    'daily_sms_count': row[4] or 0,
                    'hourly_call_count': row[5] or 0,
                    'daily_call_count': row[6] or 0,
                    'last_batch_sent_at': row[7],
                    'last_call_time': row[8],
                    'last_hourly_reset': row[9],
                    'last_reset_date': row[10],
                    'is_active': bool(row[11]),
                    'total_calls_made': row[12] or 0,
                    'sms_capacity_hourly': f"{row[3] or 0}/{self.SMS_HOURLY_LIMIT}",
                    'sms_capacity_daily': f"{row[4] or 0}/{self.SMS_DAILY_LIMIT}",
                    'call_capacity_hourly': f"{row[5] or 0}/{self.CALL_HOURLY_LIMIT}",
                    'call_capacity_daily': f"{row[6] or 0}/{self.CALL_DAILY_LIMIT}"
                }
            else:
                return None
        
        finally:
            cursor.close()
            conn.close()
    
    def get_store_capacity(self, store_id: int, usage_type: Literal['sms', 'call'] = 'sms') -> Dict[str, Any]:
        """
        Get capacity summary for all numbers assigned to a store.
        
        Useful for campaign preview and capacity planning.
        
        Args:
            store_id: Store ID to check capacity for
            usage_type: 'sms' or 'call' to check appropriate limits
        
        Returns:
            Dict with capacity summary:
            {
                'store_id': int,
                'total_numbers': int,
                'available_numbers': int,
                'numbers_at_capacity': int,
                'estimated_remaining_capacity': int  # rough estimate
            }
        """
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            if usage_type == 'sms':
                # Count total numbers for store
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM TwilioNumbers
                    WHERE is_active = 1
                      AND (store_id = ? OR store_id IS NULL)
                """, store_id)
                total_numbers = cursor.fetchone()[0]
                
                # Count available numbers (under limits and off cooldown)
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM TwilioNumbers
                    WHERE is_active = 1
                      AND (store_id = ? OR store_id IS NULL)
                      AND (hourly_sms_count < ? OR hourly_sms_count IS NULL)
                      AND (daily_sms_count < ? OR daily_sms_count IS NULL)
                      AND (
                          last_batch_sent_at IS NULL 
                          OR last_batch_sent_at < DATEADD(MINUTE, -?, GETDATE())
                      )
                """, store_id, self.SMS_HOURLY_LIMIT, self.SMS_DAILY_LIMIT, self.SMS_BATCH_COOLDOWN_MINUTES)
                available_numbers = cursor.fetchone()[0]
                
                # Rough capacity estimate (available numbers * remaining daily capacity)
                cursor.execute("""
                    SELECT SUM(? - ISNULL(daily_sms_count, 0))
                    FROM TwilioNumbers
                    WHERE is_active = 1
                      AND (store_id = ? OR store_id IS NULL)
                      AND (daily_sms_count < ? OR daily_sms_count IS NULL)
                """, self.SMS_DAILY_LIMIT, store_id, self.SMS_DAILY_LIMIT)
                remaining_capacity = cursor.fetchone()[0] or 0
            
            elif usage_type == 'call':
                # Count total numbers for store
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM TwilioNumbers
                    WHERE is_active = 1
                      AND (store_id = ? OR store_id IS NULL)
                """, store_id)
                total_numbers = cursor.fetchone()[0]
                
                # Count available numbers (under limits and off cooldown)
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM TwilioNumbers
                    WHERE is_active = 1
                      AND (store_id = ? OR store_id IS NULL)
                      AND (hourly_call_count < ? OR hourly_call_count IS NULL)
                      AND (daily_call_count < ? OR daily_call_count IS NULL)
                      AND (
                          last_call_time IS NULL 
                          OR last_call_time < DATEADD(MINUTE, -?, GETDATE())
                      )
                """, store_id, self.CALL_HOURLY_LIMIT, self.CALL_DAILY_LIMIT, self.CALL_COOLDOWN_MINUTES)
                available_numbers = cursor.fetchone()[0]
                
                # Rough capacity estimate
                cursor.execute("""
                    SELECT SUM(? - ISNULL(daily_call_count, 0))
                    FROM TwilioNumbers
                    WHERE is_active = 1
                      AND (store_id = ? OR store_id IS NULL)
                      AND (daily_call_count < ? OR daily_call_count IS NULL)
                """, self.CALL_DAILY_LIMIT, store_id, self.CALL_DAILY_LIMIT)
                remaining_capacity = cursor.fetchone()[0] or 0
            
            else:
                raise ValueError(f"Invalid usage_type: {usage_type}")
            
            return {
                'store_id': store_id,
                'usage_type': usage_type,
                'total_numbers': total_numbers,
                'available_numbers': available_numbers,
                'numbers_at_capacity': total_numbers - available_numbers,
                'estimated_remaining_capacity': max(0, remaining_capacity)
            }
        
        finally:
            cursor.close()
            conn.close()
    
    def reset_hourly_stats(self) -> int:
        """
        Reset hourly counters for numbers where last reset was over 1 hour ago.
        
        This should be called by a cron job every hour.
        
        Returns:
            Number of phone numbers reset
        """
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Use the stored procedure created in migration
            cursor.execute("EXEC reset_hourly_phone_stats")
            result = cursor.fetchone()
            rows_reset = result[0] if result else 0
            
            conn.commit()
            return rows_reset
        
        except Exception as e:
            conn.rollback()
            print(f"❌ Error resetting hourly stats: {e}")
            return 0
        
        finally:
            cursor.close()
            conn.close()
    
    def reset_daily_stats(self) -> int:
        """
        Reset daily counters for numbers that haven't been reset today.
        
        This should be called by a cron job once per day (e.g., midnight).
        
        Returns:
            Number of phone numbers reset
        """
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Use the stored procedure created in migration
            cursor.execute("EXEC reset_daily_phone_stats")
            result = cursor.fetchone()
            rows_reset = result[0] if result else 0
            
            conn.commit()
            return rows_reset
        
        except Exception as e:
            conn.rollback()
            print(f"❌ Error resetting daily stats: {e}")
            return 0
        
        finally:
            cursor.close()
            conn.close()


if __name__ == "__main__":
    """Quick test of phone pool manager."""
    print("=" * 70)
    print("Phone Number Pool Manager - Quick Test")
    print("=" * 70)
    
    manager = PhoneNumberPoolManager()
    
    # Test 1: Get next available number for SMS (store 1)
    print("\n[TEST 1] Getting next available number for SMS (store_id=1)...")
    number = manager.get_next_available_number(store_id=1, usage_type='sms')
    if number:
        print(f"✅ Selected number: {number['phone_number']}")
        print(f"   Hourly SMS: {number['hourly_sms_count']}/{manager.SMS_HOURLY_LIMIT}")
        print(f"   Daily SMS: {number['daily_sms_count']}/{manager.SMS_DAILY_LIMIT}")
    else:
        print("❌ No available numbers (all at capacity or on cooldown)")
    
    # Test 2: Get store capacity
    print("\n[TEST 2] Getting store capacity...")
    capacity = manager.get_store_capacity(store_id=1, usage_type='sms')
    print(f"✅ Store 1 SMS Capacity:")
    print(f"   Total numbers: {capacity['total_numbers']}")
    print(f"   Available now: {capacity['available_numbers']}")
    print(f"   At capacity: {capacity['numbers_at_capacity']}")
    print(f"   Estimated remaining: {capacity['estimated_remaining_capacity']} SMS")
    
    print("\n" + "=" * 70)

