#!/usr/bin/env python3
"""
SMS Campaign Manager
Handles campaign creation and batch scheduling WITHOUT sending any SMS.

Key Safety Feature: This module ONLY creates database records.
SMS sending happens later in Milestone 9 with explicit user confirmation.

Core Responsibilities:
1. Create campaign records in sms_campaigns table
2. Schedule batches with 25 leads each, 60 minutes (1 hour) apart
3. Assign leads to batches (create batch_lead_mapping records)
4. Calculate campaign estimates (cost, time, batch count)

Rate Limiting Strategy:
- Batch size: 25 leads per batch (fixed, matches hourly SMS limit)
- Batch spacing: 60 minutes (1 hour) between batches to allow hourly limit reset
- Phone number assignment: Dynamic during execution (not done here)

Database Tables Used:
- sms_campaigns: Campaign metadata
- sms_batches: Batch scheduling records
- batch_lead_mapping: Lead-to-batch assignments
- OutboundLeads: Lead data (filtered by store_id, dnc_flag, etc.)
"""

import os
import sys
import pyodbc
import asyncio
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from dotenv import load_dotenv
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

load_dotenv()

# Import config for SMS consent cooldown period
from config import config

# SQL Server configuration
SQL_SERVER = os.getenv('SQLServer')
SQL_USER = os.getenv('SQLUser')
SQL_PASSWORD = os.getenv('SQLPassword')
SQL_DATABASE = os.getenv('SQLDatabase')

# Twilio configuration
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')


class SMSCampaignManager:
    """
    Manages SMS campaign creation and batch scheduling.
    
    ⚠️ CRITICAL SAFETY: This class DOES NOT send any SMS messages.
    It only creates database records for scheduled batches.
    
    Usage:
        manager = SMSCampaignManager()
        
        # Create campaign (NO SMS SENT)
        result = manager.create_campaign(
            store_id=1,
            target_count=50,
            start_time=datetime(2025, 11, 14, 9, 0, 0)
        )
        
        print(f"Campaign created: {result['campaign_id']}")
        print(f"Batches scheduled: {result['batch_count']}")
        print(f"SMS sent: {result['sms_sent']}")  # Always False
    """
    
    # Campaign constants
    BATCH_SIZE = 25
    BATCH_SPACING_MINUTES = 60 
    SMS_COST_PER_MESSAGE = 0.0083  # Twilio SMS cost: $0.0083 per message
    
    def __init__(self):
        """Initialize the campaign manager."""
        self.connection_string = (
            f"DRIVER={{ODBC Driver 18 for SQL Server}};TrustServerCertificate=yes;"
            f"SERVER={SQL_SERVER};"
            f"DATABASE={SQL_DATABASE};"
            f"UID={SQL_USER};"
            f"PWD={SQL_PASSWORD}"
        )
    
    def get_db_connection(self):
        """Get database connection."""
        return pyodbc.connect(self.connection_string)
    
    def create_campaign(
        self,
        store_id: int,
        target_count: int,
        start_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Create SMS campaign with scheduled batches.
        
        ⚠️ CRITICAL: This method DOES NOT send any SMS messages.
        It only creates database records with status='pending'.
        
        Process:
        1. Validate store exists and is active
        2. Fetch eligible leads (store_id, not on DNC, no prior SMS)
        3. Create campaign record in sms_campaigns table
        4. Calculate batch count (target_count ÷ 25)
        5. Create batch records with scheduled times (60 min apart)
        6. Assign leads to batches (create batch_lead_mapping records)
        
        Args:
            store_id: Store ID for the campaign
            target_count: Number of leads to contact (max available)
            start_time: Campaign start time (default: now + 30 minutes)
        
        Returns:
            Dict with campaign details:
            {
                'campaign_id': int,
                'store_id': int,
                'target_count': int,
                'actual_leads_assigned': int,
                'batch_count': int,
                'estimated_cost': float,
                'estimated_duration_minutes': int,
                'start_time': datetime,
                'batches': [
                    {
                        'batch_id': int,
                        'batch_number': int,
                        'scheduled_at': datetime,
                        'lead_count': int
                    }
                ],
                'sms_sent': False  ← CRITICAL
            }
        
        Raises:
            ValueError: If store_id invalid or no eligible leads found
            Exception: If database operation fails
        """
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # ================================================================
            # STEP 1: Validate store exists and is active
            # ================================================================
            cursor.execute("""
                SELECT store_id, name, is_active
                FROM stores
                WHERE store_id = ?
            """, (store_id,))
            
            store = cursor.fetchone()
            if not store:
                raise ValueError(f"Store ID {store_id} not found")
            
            if not store[2]:  # is_active
                raise ValueError(f"Store ID {store_id} is not active")
            
            # ================================================================
            # STEP 2: Fetch eligible leads for this store
            # ================================================================
            
            # First try store-assigned leads (matching preview endpoint criteria)
            # ORDER BY NEWID() for randomization to prevent carrier spam detection
            # ⚠️ CRITICAL: Exclude leads already assigned to other campaigns/batches
            # ⚠️ CRITICAL: Exclude leads that already received SMS consent request within cooldown
            # ⚠️ CRITICAL: Use DISTINCT to prevent duplicate lead_ids in result set
            # Eligibility: (never sent consent SMS) OR (sent more than cooldown days ago)
            # Do NOT select leads already in a progressing campaign.
            # sms_batches.status defined in core/schema.py: 'pending', 'executing', 'completed', 'failed'
            cooldown_days = config.campaign.SMS_CONSENT_COOLDOWN_DAYS
            # Use subquery to handle DISTINCT with ORDER BY NEWID()
            cursor.execute("""
                SELECT TOP (?)
                    lead_id, 
                    phone_number, 
                    Name, 
                    City, 
                    State
                FROM (
                    SELECT DISTINCT
                        ol.lead_id, 
                        ol.phone_number, 
                        ol.Name, 
                        ol.City, 
                        ol.State,
                        CASE WHEN ol.priority IS NOT NULL THEN ol.priority ELSE 999 END as priority_value
                    FROM OutboundLeads ol
                    WHERE ol.store_id = ?
                      AND (ol.dnc_flag = 0 OR ol.dnc_flag IS NULL)
                      AND (
                          -- Never sent SMS consent request OR sent more than cooldown days ago
                          ol.sms_consent_requested_at IS NULL
                          OR ol.sms_consent_requested_at < DATEADD(day, -?, GETDATE())
                      )
                      AND NOT EXISTS (
                          -- Exclude leads in batches not yet completed (pending or executing only)
                          SELECT 1
                          FROM batch_lead_mapping blm
                          INNER JOIN sms_batches b ON blm.batch_id = b.batch_id
                          WHERE blm.lead_id = ol.lead_id
                            AND b.status IN ('pending', 'executing')
                      )
                ) AS distinct_leads
                ORDER BY 
                    priority_value ASC,
                    NEWID()
            """, (target_count, store_id, cooldown_days))
            
            eligible_leads = cursor.fetchall()
            actual_lead_count = len(eligible_leads)
            
            # If no store-assigned leads, try unassigned leads (fallback, matching preview)
            if actual_lead_count == 0:
                print(f"   No store-assigned leads found, checking unassigned leads...")
                cooldown_days = config.campaign.SMS_CONSENT_COOLDOWN_DAYS
                # Use subquery to handle DISTINCT with ORDER BY NEWID()
                cursor.execute("""
                    SELECT TOP (?)
                        lead_id, 
                        phone_number, 
                        Name, 
                        City, 
                        State
                    FROM (
                        SELECT DISTINCT
                            ol.lead_id, 
                            ol.phone_number, 
                            ol.Name, 
                            ol.City, 
                            ol.State,
                            CASE WHEN ol.priority IS NOT NULL THEN ol.priority ELSE 999 END as priority_value
                        FROM OutboundLeads ol
                        WHERE ol.store_id IS NULL
                          AND (ol.dnc_flag = 0 OR ol.dnc_flag IS NULL)
                          AND (
                              -- Never sent SMS consent request OR sent more than cooldown days ago
                              ol.sms_consent_requested_at IS NULL
                              OR ol.sms_consent_requested_at < DATEADD(day, -?, GETDATE())
                          )
                          AND NOT EXISTS (
                              -- Exclude leads in batches not yet completed (pending or executing)
                              SELECT 1
                              FROM batch_lead_mapping blm
                              INNER JOIN sms_batches b ON blm.batch_id = b.batch_id
                              WHERE blm.lead_id = ol.lead_id
                                AND b.status IN ('pending', 'executing')
                          )
                    ) AS distinct_leads
                    ORDER BY 
                        priority_value ASC,
                        NEWID()
                """, (target_count, cooldown_days))
                
                eligible_leads = cursor.fetchall()
                actual_lead_count = len(eligible_leads)
                
            if actual_lead_count == 0:
                # Get more detailed information for better error message
                cursor.execute("""
                    SELECT COUNT(*) as total_leads
                    FROM OutboundLeads
                    WHERE store_id = ? OR store_id IS NULL
                """, (store_id,))
                total_leads = cursor.fetchone()[0] or 0
                
                cooldown_days = config.campaign.SMS_CONSENT_COOLDOWN_DAYS
                cursor.execute("""
                    SELECT 
                        COUNT(*) as dnc_count,
                        SUM(CASE WHEN sms_verified = 1 THEN 1 ELSE 0 END) as verified_count,
                        SUM(CASE WHEN sms_consent_requested_at >= DATEADD(day, -?, GETDATE()) THEN 1 ELSE 0 END) as recent_consent_count
                    FROM OutboundLeads
                    WHERE store_id = ? OR store_id IS NULL
                """, (cooldown_days, store_id))
                stats = cursor.fetchone()
                dnc_count = stats[0] or 0 if stats else 0
                verified_count = stats[1] or 0 if stats else 0
                recent_consent_count = stats[2] or 0 if stats else 0
                
                cooldown_days = config.campaign.SMS_CONSENT_COOLDOWN_DAYS
                error_msg = (
                    f"No eligible leads found for store_id={store_id}. "
                    f"Leads must be: not on DNC, never sent consent SMS or sent >{cooldown_days} days ago, and not already in a progressing campaign.\n"
                    f"Total leads for store: {total_leads}\n"
                    f"- On DNC: {dnc_count}\n"
                    f"- Already verified (within {cooldown_days} days): {verified_count}\n"
                    f"- Consent requested in last {cooldown_days} days: {recent_consent_count}\n"
                    f"Note: Leads are only eligible if they have never been sent an SMS consent request or it was sent more than {cooldown_days} days ago."
                )
                print(f"[SMSCampaignManager] ERROR: {error_msg}")
                raise ValueError(error_msg)
            
            # ================================================================
            # STEP 3: Create campaign record
            # ================================================================
            
            if start_time is None:
                # Default to now so batches can execute immediately
                start_time = datetime.now()
            
            cursor.execute("""
                INSERT INTO sms_campaigns (
                    store_id, target_count, actual_sent, status, started_at, created_at
                )
                VALUES (?, ?, 0, 'pending', ?, GETDATE())
            """, store_id, actual_lead_count, start_time)
            
            # Get the created campaign_id
            cursor.execute("SELECT @@IDENTITY")
            campaign_id = int(cursor.fetchone()[0])
            
            # ================================================================
            # STEP 4: Calculate batches and schedule times
            # ================================================================
            print(f"\n[Campaign Manager] Calculating batch schedule...")
            
            batch_count = (actual_lead_count + self.BATCH_SIZE - 1) // self.BATCH_SIZE  # Ceiling division
            batches_created = []
            
            # ================================================================
            # STEP 5: Create batch records and assign leads
            # ================================================================
            
            lead_index = 0
            # Track leads assigned in this campaign to prevent duplicates across batches
            assigned_lead_ids_in_campaign = set()
            
            for batch_num in range(1, batch_count + 1):
                # Calculate scheduled time for this batch
                scheduled_at = start_time + timedelta(minutes=(batch_num - 1) * self.BATCH_SPACING_MINUTES)
                
                # Ensure batch is scheduled within business hours (9AM-6PM)
                while scheduled_at.hour < 9 or scheduled_at.hour >= 18:
                    if scheduled_at.hour < 9:
                        # Before 9AM - move to 9AM same day
                        scheduled_at = scheduled_at.replace(hour=9, minute=0, second=0)
                    else:
                        # After 6PM - move to 9AM next day
                        scheduled_at = (scheduled_at + timedelta(days=1)).replace(hour=9, minute=0, second=0)
                
                # Determine how many leads for this batch
                leads_remaining = actual_lead_count - lead_index
                batch_lead_count = min(self.BATCH_SIZE, leads_remaining)
                
                # Create batch record (twilio_number_id is NULL - assigned during execution)
                cursor.execute("""
                    INSERT INTO sms_batches (
                        campaign_id,
                        twilio_number_id,
                        batch_number,
                        target_count,
                        actual_sent,
                        scheduled_at,
                        status,
                        created_at
                    )
                    VALUES (?, NULL, ?, ?, 0, ?, 'pending', GETDATE())
                """, campaign_id, batch_num, batch_lead_count, scheduled_at)
                
                # Get the created batch_id
                cursor.execute("SELECT @@IDENTITY")
                batch_id = int(cursor.fetchone()[0])
                
                # Assign leads to this batch
                batch_leads = eligible_leads[lead_index:lead_index + batch_lead_count]
                
                for lead_row in batch_leads:
                    lead_id = lead_row[0]
                    
                    # ⚠️ CRITICAL: Prevent duplicate lead assignment within same campaign
                    # (UNIQUE constraint prevents same lead in same batch, but not across batches)
                    if lead_id in assigned_lead_ids_in_campaign:
                        print(f"⚠️ SKIPPED: Lead {lead_id} already assigned to another batch in this campaign")
                        continue
                    
                    try:
                        cursor.execute("""
                            INSERT INTO batch_lead_mapping (batch_id, lead_id, assigned_at)
                            VALUES (?, ?, GETDATE())
                        """, batch_id, lead_id)
                        assigned_lead_ids_in_campaign.add(lead_id)
                    except Exception as e:
                        # Handle UNIQUE constraint violation (shouldn't happen with DISTINCT, but safety check)
                        if "UNIQUE" in str(e) or "duplicate" in str(e).lower():
                            print(f"⚠️ SKIPPED: Lead {lead_id} duplicate detected (already in batch_lead_mapping): {e}")
                            continue
                        raise  # Re-raise if it's a different error
                
                batches_created.append({
                    'batch_id': batch_id,
                    'batch_number': batch_num,
                    'scheduled_at': scheduled_at,
                    'lead_count': batch_lead_count
                })
                
                lead_index += batch_lead_count
            
            # ================================================================
            # STEP 6: Commit transaction
            # ================================================================
            conn.commit()
            
            # ================================================================
            # STEP 7: Calculate estimates
            # ================================================================
            estimated_cost = actual_lead_count * self.SMS_COST_PER_MESSAGE
            estimated_duration_minutes = (batch_count - 1) * self.BATCH_SPACING_MINUTES + 5  # +5 for last batch execution
            
            # ================================================================
            # STEP 8: Return campaign details
            # ================================================================
            result = {
                'campaign_id': campaign_id,
                'store_id': store_id,
                'store_name': store[1],
                'target_count': target_count,
                'actual_leads_assigned': actual_lead_count,
                'batch_count': batch_count,
                'batch_size': self.BATCH_SIZE,
                'batch_spacing_minutes': self.BATCH_SPACING_MINUTES,
                'estimated_cost': round(estimated_cost, 2),
                'estimated_duration_minutes': estimated_duration_minutes,
                'start_time': start_time,
                'batches': batches_created,
                'status': 'pending',
                'sms_sent': False  # ← CRITICAL: No SMS sent during campaign creation
            }
            
            print(f"\n{'='*70}")
            print(f"✅ CAMPAIGN CREATED AND SCHEDULED")
            print(f"{'='*70}")
            print(f"Campaign ID: {campaign_id}")
            print(f"Store: {store[1]} (ID: {store_id})")
            print(f"Leads assigned: {actual_lead_count}")
            print(f"Batches scheduled: {batch_count}")
            print(f"Estimated cost: ${estimated_cost:.2f}")
            print(f"Estimated duration: {estimated_duration_minutes} minutes")
            print(f"Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"\n⚠️  IMPORTANT: NO SMS MESSAGES SENT YET")
            print(f"   Batches are scheduled with status='pending'")
            print(f"   SMS will be sent in Milestone 9 after explicit confirmation")
            print(f"{'='*70}\n")
            
            return result
        
        except Exception as e:
            conn.rollback()
            print(f"\n❌ Campaign creation failed: {e}")
            raise
        
        finally:
            cursor.close()
            conn.close()
    
    def get_campaign_details(self, campaign_id: int) -> Optional[Dict[str, Any]]:
        """
        Get full details of a campaign including all batches.
        
        Args:
            campaign_id: Campaign ID to fetch
        
        Returns:
            Dict with campaign details, or None if not found
        """
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Fetch campaign record
            cursor.execute("""
                SELECT 
                    c.campaign_id,
                    c.store_id,
                    s.name as store_name,
                    c.target_count,
                    c.actual_sent,
                    c.status,
                    c.started_at,
                    c.completed_at,
                    c.created_at
                FROM sms_campaigns c
                JOIN stores s ON c.store_id = s.store_id
                WHERE c.campaign_id = ?
            """, campaign_id)
            
            campaign_row = cursor.fetchone()
            if not campaign_row:
                return None
            
            # Fetch batches for this campaign
            cursor.execute("""
                SELECT 
                    batch_id,
                    batch_number,
                    twilio_number_id,
                    target_count,
                    actual_sent,
                    scheduled_at,
                    status,
                    started_at,
                    completed_at
                FROM sms_batches
                WHERE campaign_id = ?
                ORDER BY batch_number ASC
            """, campaign_id)
            
            batches = []
            for batch_row in cursor.fetchall():
                batches.append({
                    'batch_id': batch_row[0],
                    'batch_number': batch_row[1],
                    'twilio_number_id': batch_row[2],
                    'target_count': batch_row[3],
                    'actual_sent': batch_row[4],
                    'scheduled_at': batch_row[5],
                    'status': batch_row[6],
                    'started_at': batch_row[7],
                    'completed_at': batch_row[8]
                })
            
            return {
                'campaign_id': campaign_row[0],
                'store_id': campaign_row[1],
                'store_name': campaign_row[2],
                'target_count': campaign_row[3],
                'actual_sent': campaign_row[4],
                'status': campaign_row[5],
                'started_at': campaign_row[6],
                'completed_at': campaign_row[7],
                'created_at': campaign_row[8],
                'batch_count': len(batches),
                'batches': batches
            }
        
        finally:
            cursor.close()
            conn.close()
    
    def get_templates_for_store(self, store_id: int) -> List[Dict[str, Any]]:
        """
        Get all active SMS templates for a store (including shared templates).
        
        Args:
            store_id: Store ID to fetch templates for
        
        Returns:
            List of template dictionaries
        """
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT template_id, template_name, template_content
                FROM sms_templates
                WHERE is_active = 1
                ORDER BY template_id
            """)
            
            templates = []
            for row in cursor.fetchall():
                templates.append({
                    'template_id': row[0],
                    'template_name': row[1] or f"Template {row[0]}",
                    'template_text': row[2]
                })
            
            return templates
        
        finally:
            cursor.close()
            conn.close()
    
    def _get_all_available_numbers_with_webhook(self, store_id: int, conn) -> List[Dict[str, Any]]:
        """
        Get all available phone numbers for a store that have SMS webhook configured.
        
        Args:
            store_id: Store ID to filter numbers
            conn: Database connection
            
        Returns:
            List of available number dicts with webhook configured
        """
        from utils.phone_pool_manager import PhoneNumberPoolManager
        from config import config
        
        phone_pool_manager = PhoneNumberPoolManager()
        cursor = conn.cursor()
        
        try:
            # Get all available numbers from database (under limits, active, etc.)
            query = """
                SELECT 
                    number_id,
                    phone_number,
                    store_id,
                    hourly_sms_count,
                    daily_sms_count,
                    last_batch_sent_at
                FROM TwilioNumbers
                WHERE is_active = 1
                  AND store_id = ?
                  AND (hourly_sms_count < 25 OR hourly_sms_count IS NULL)
                  AND (daily_sms_count < 50 OR daily_sms_count IS NULL)
                  AND (
                      last_batch_sent_at IS NULL 
                      OR last_batch_sent_at < DATEADD(MINUTE, -20, GETDATE())
                  )
                ORDER BY 
                    CASE WHEN last_batch_sent_at IS NULL THEN 0 ELSE 1 END,
                    last_batch_sent_at ASC
            """
            cursor.execute(query, store_id)
            rows = cursor.fetchall()
            
            available_numbers = []
            twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            
            # Expected webhook URL patterns - must match actual endpoint paths
            # Supports both root-level (/twilio-sms) and prefixed (/sms/twilio-sms) endpoints
            expected_webhook_patterns = ["/twilio-sms", "/sms/twilio-sms", "twilio-sms"]
            
            for row in rows:
                number_id = row[0]
                phone_number = row[1]
                
                # Check if number has SMS webhook configured via Twilio API
                try:
                    # Fetch the phone number from Twilio to check webhook configuration
                    twilio_number = twilio_client.incoming_phone_numbers.list(phone_number=phone_number)
                    
                    if twilio_number:
                        number_obj = twilio_number[0]
                        sms_url = number_obj.sms_url or ""
                        
                        # Check if webhook URL is configured (check for any of the expected patterns)
                        # More specific: check for exact path patterns to avoid false positives
                        has_webhook = sms_url and any(
                            pattern in sms_url.lower() for pattern in expected_webhook_patterns
                        )
                        if has_webhook:
                            available_numbers.append({
                                'number_id': number_id,
                                'phone_number': phone_number,
                                'store_id': row[2],
                                'hourly_sms_count': row[3] or 0,
                                'daily_sms_count': row[4] or 0,
                                'last_batch_sent_at': row[5]
                            })
                            print(f"✅ Number {phone_number} has webhook configured: {sms_url}")
                        else:
                            print(f"⚠️ Number {phone_number} missing SMS webhook (URL: {sms_url or 'None'})")
                    else:
                        print(f"⚠️ Number {phone_number} not found in Twilio account")
                except Exception as e:
                    print(f"⚠️ Error checking webhook for {phone_number}: {e}")
                    # Continue to next number instead of failing completely
                    continue
            
            return available_numbers
            
        finally:
            cursor.close()
    
    async def execute_batch(self, batch_id: int) -> Dict[str, Any]:
        """
        Execute a scheduled SMS batch - THIS SENDS REAL SMS MESSAGES.
        
        ⚠️ CRITICAL: This method ACTUALLY SENDS SMS via Twilio and incurs charges!
        
        Process:
        1. Validate batch exists and is pending
        2. Get next available phone number from pool
        3. Fetch leads assigned to this batch
        4. Get templates for the store
        5. For each lead:
           - Select random template
           - Render template with lead data
           - Send SMS via Twilio API
           - Update lead's sms_consent_requested_at timestamp
           - Wait 1 second (rate limiting)
        6. Update phone number counters
        7. Update batch status to 'completed'
        8. Update campaign actual_sent count
        
        Args:
            batch_id: Batch ID to execute
        
        Returns:
            Dict with execution results:
            {
                'batch_id': int,
                'campaign_id': int,
                'phone_number_used': str,
                'target_count': int,
                'actual_sent': int,
                'failed_count': int,
                'errors': List[Dict],
                'duration_seconds': float,
                'status': 'completed' or 'failed'
            }
        
        Raises:
            ValueError: If batch not found, already executed, or no phone numbers available
            Exception: If Twilio API fails or database error occurs
        """
        import random
        from utils.phone_pool_manager import PhoneNumberPoolManager
        from utils.template_renderer import render_template
        
        start_time = time.time()
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        # Initialize Twilio client
        if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
            raise ValueError("Twilio credentials not configured. Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN in .env")
        
        twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        phone_pool_manager = PhoneNumberPoolManager()
        
        try:
            print(f"[Batch Executor] Executing batch {batch_id}...")
            
            # ================================================================
            # STEP 1: Validate batch exists and is pending
            # ================================================================
            cursor.execute("""
                SELECT 
                    b.batch_id,
                    b.campaign_id,
                    b.batch_number,
                    b.target_count,
                    b.status,
                    b.scheduled_at,
                    c.store_id,
                    s.name as store_name
                FROM sms_batches b
                JOIN sms_campaigns c ON b.campaign_id = c.campaign_id
                JOIN stores s ON c.store_id = s.store_id
                WHERE b.batch_id = ?
            """, batch_id)
            
            batch_row = cursor.fetchone()
            if not batch_row:
                raise ValueError(f"Batch ID {batch_id} not found")
            
            batch_status = batch_row[4]
            if batch_status != 'pending':
                raise ValueError(f"Batch {batch_id} status is '{batch_status}'. Only 'pending' batches can be executed.")
            
            campaign_id = batch_row[1]
            batch_number = batch_row[2]
            target_count = batch_row[3]
            store_id = batch_row[6]
            store_name = batch_row[7]
            
            # ================================================================
            # STEP 2: Get ALL available phone numbers for the store
            # (We'll try different numbers for each lead if needed)
            # ================================================================
            available_numbers = self._get_all_available_numbers_with_webhook(store_id, conn)
            
            if not available_numbers:
                raise ValueError(f"No available phone numbers with SMS webhook configured for store_id={store_id}. All numbers at capacity, on cooldown, or missing webhook.")
            
            print(f"[Batch Executor] Found {len(available_numbers)} available number(s) with webhook configured for store_id={store_id}")
            webhook_number_ids = [number['number_id'] for number in available_numbers]
            
            # Update batch status to executing (we'll update twilio_number_id per lead)
            cursor.execute("""
                UPDATE sms_batches
                SET status = 'executing',
                    started_at = GETDATE()
                WHERE batch_id = ?
            """, batch_id)
            conn.commit()
            
            # ================================================================
            # STEP 3: Fetch leads for this batch
            # ================================================================
            cursor.execute("""
                SELECT 
                    l.lead_id,
                    l.phone_number,
                    l.Name,
                    l.City,
                    l.State,
                    l.Address,
                    l.Zip
                FROM batch_lead_mapping blm
                JOIN OutboundLeads l ON blm.lead_id = l.lead_id
                WHERE blm.batch_id = ?
                  AND (l.dnc_flag = 0 OR l.dnc_flag IS NULL)
                ORDER BY blm.assigned_at ASC
            """, batch_id)
            
            leads = cursor.fetchall()
            lead_count = len(leads)
            
            if lead_count == 0:
                raise ValueError(f"No leads found for batch_id={batch_id}")
            
            # ================================================================
            # STEP 4: Get templates for the store
            # ================================================================
            templates = self.get_templates_for_store(store_id)
            
            if not templates:
                raise ValueError(f"No active templates found for store_id={store_id}")
            
            # Shuffle templates at the start of batch for better distribution
            # This ensures templates are used more evenly across the batch
            random.shuffle(templates)
            print(f"[Batch Executor] Loaded {len(templates)} active template(s) for rotation")
            
            # Track template usage within batch to avoid immediate repeats and for reporting
            # (Optional: ensures variety even within small batches)
            template_usage_tracker = {}  # {template_id: count}
            last_template_id = None
            
            # ================================================================
            # STEP 5: Send SMS to each lead (with anti-spam spacing)
            # ================================================================
            
            sent_count = 0
            failed_count = 0
            errors = []
            
            # Retry queue for temporarily failed leads (e.g., unreachable handset)
            # These will be retried after the main batch completes
            retry_queue = []  # List of (lead_row, error_code, attempt_count)
            RETRYABLE_ERROR_CODES = [30003]  # 30003 = Unreachable destination handset
            MAX_RETRY_ATTEMPTS = 2
            RETRY_DELAY_SECONDS = 60  # Wait 60 seconds before retry
            
            # Anti-spam delay: 4-5 seconds between SMS sends to avoid carrier spam detection
            SMS_SEND_DELAY_MIN = 4.0  # Minimum seconds between sends
            SMS_SEND_DELAY_MAX = 5.0  # Maximum seconds between sends
            
            for idx, lead_row in enumerate(leads, 1):
                # Add delay between SMS sends (skip delay for first message)
                if idx > 1 and sent_count > 0:
                    delay = random.uniform(SMS_SEND_DELAY_MIN, SMS_SEND_DELAY_MAX)
                    print(f"   ⏳ Anti-spam delay: waiting {delay:.1f}s before next SMS...")
                    time.sleep(delay)
                
                lead_id = lead_row[0]
                to_phone = lead_row[1]
                lead_name = lead_row[2] or "there"
                lead_city = lead_row[3] or ""
                lead_state = lead_row[4] or ""
                
                selected_number = phone_pool_manager.reserve_next_available_number(
                    store_id=store_id,
                    usage_type='sms',
                    excluded_phone=to_phone,
                    allowed_number_ids=webhook_number_ids,
                )

                if not selected_number:
                    error_msg = (
                        f"Cannot send SMS: No reservable Twilio numbers for store_id={store_id}. "
                        "All webhook-configured numbers are at capacity, on cooldown, or match "
                        f"the lead's phone number ({to_phone})."
                    )
                    
                    errors.append({
                        'lead_id': lead_id,
                        'phone_number': to_phone,
                        'error': error_msg,
                        'error_code': 'NO_SELECTABLE_NUMBERS'
                    })
                    failed_count += 1
                    print(f"⚠️ SKIPPED Lead {lead_id}: {error_msg}")
                    continue
                
                from_phone = selected_number['phone_number']
                twilio_number_id = selected_number['number_id']
                
                print(f"📱 Selected number {from_phone} for Lead {lead_id} (lead phone: {to_phone})")
                
                # ================================================================
                # Pre-send validation: Check PhoneStatus before sending (Milestone 2)
                # ================================================================
                try:
                    from services.phone_status_service import get_phone_status_service
                    phone_status_service = get_phone_status_service()
                    allowed_check = phone_status_service.should_allow_sms(to_phone)
                    
                    if not allowed_check.get('allowed', True):
                        reason = allowed_check.get('reason', 'Unknown')
                        errors.append({
                            'lead_id': lead_id,
                            'phone_number': to_phone,
                            'error': f"SMS blocked by PhoneStatus: {reason}",
                            'error_code': 'PHONESTATUS_BLOCKED',
                            'block_reason': reason
                        })
                        failed_count += 1
                        print(f"⛔ SMS blocked for Lead {lead_id} ({to_phone}): {reason}")
                        continue
                except Exception as ps_error:
                    # If PhoneStatus check fails, log warning but allow send to proceed
                    print(f"⚠️  Warning: PhoneStatus check failed for {to_phone}: {ps_error}. Proceeding with send...")
                
                # ================================================================
                # Pre-send validation: Trestle Real Contact API validation
                # Rules: activity_score > 30 AND line_type = Mobile
                # ================================================================
                try:
                    from config import config
                    if config.trestle.VALIDATE_BEFORE_SMS and config.trestle.API_KEY:
                        from services.trestle_service import get_trestle_service, MIN_ACTIVITY_SCORE_FOR_SMS
                        trestle_service = get_trestle_service()
                        # Pass lead name to API for better validation results
                        validation = trestle_service.validate_phone_sync(to_phone, name=lead_name)
                        
                        activity_score = validation.get('activity_score')
                        line_type = validation.get('line_type', 'Unknown')
                        contact_grade = validation.get('contact_grade')
                        is_valid = validation.get('is_valid', True)
                        
                        # Block invalid numbers
                        if not is_valid:
                            error_msg = "Invalid phone number (Trestle validation failed)"
                            errors.append({
                                'lead_id': lead_id,
                                'phone_number': to_phone,
                                'error': error_msg,
                                'error_code': 'TRESTLE_INVALID',
                                'line_type': line_type,
                                'activity_score': activity_score
                            })
                            # Update batch_lead_mapping with failure
                            try:
                                cursor.execute("""
                                    UPDATE batch_lead_mapping
                                    SET status = 'failed', error_message = ?
                                    WHERE batch_id = ? AND lead_id = ?
                                """, (error_msg, batch_id, lead_id))
                                conn.commit()
                            except: pass
                            failed_count += 1
                            print(f"⛔ SMS blocked for Lead {lead_id} ({to_phone}): Invalid number")
                            continue
                        
                        # Block low activity score (disconnected/inactive numbers)
                        if activity_score is not None and activity_score <= MIN_ACTIVITY_SCORE_FOR_SMS:
                            error_msg = f"Low activity score ({activity_score}) - number likely disconnected/inactive"
                            errors.append({
                                'lead_id': lead_id,
                                'phone_number': to_phone,
                                'error': error_msg,
                                'error_code': 'TRESTLE_LOW_ACTIVITY',
                                'activity_score': activity_score,
                                'line_type': line_type
                            })
                            # Update batch_lead_mapping with failure
                            try:
                                cursor.execute("""
                                    UPDATE batch_lead_mapping
                                    SET status = 'failed', error_message = ?
                                    WHERE batch_id = ? AND lead_id = ?
                                """, (error_msg, batch_id, lead_id))
                                conn.commit()
                            except: pass
                            failed_count += 1
                            print(f"⛔ SMS blocked for Lead {lead_id} ({to_phone}): Low activity score ({activity_score})")
                            continue
                        
                        # Block non-Mobile numbers (only Mobile can receive SMS consent)
                        if line_type != 'Mobile':
                            error_msg = f"{line_type} number - only Mobile allowed for SMS consent"
                            errors.append({
                                'lead_id': lead_id,
                                'phone_number': to_phone,
                                'error': error_msg,
                                'error_code': 'TRESTLE_NOT_MOBILE',
                                'line_type': line_type,
                                'activity_score': activity_score
                            })
                            # Update batch_lead_mapping with failure
                            try:
                                cursor.execute("""
                                    UPDATE batch_lead_mapping
                                    SET status = 'failed', error_message = ?
                                    WHERE batch_id = ? AND lead_id = ?
                                """, (error_msg, batch_id, lead_id))
                                conn.commit()
                            except: pass
                            failed_count += 1
                            print(f"⛔ SMS blocked for Lead {lead_id} ({to_phone}): {line_type} (not Mobile)")
                            continue
                        
                        # Log validation result
                        print(f"   ✅ Trestle: {to_phone} - Mobile, activity_score={activity_score}, grade={contact_grade}")
                        
                except Exception as trestle_error:
                    # If Trestle check fails, log warning but allow send to proceed
                    print(f"⚠️  Warning: Trestle validation failed for {to_phone}: {trestle_error}. Proceeding with send...")
                
                try:
                    # Select random template with rotation logic
                    # If we have multiple templates, avoid using the same one twice in a row
                    if len(templates) > 1 and last_template_id is not None:
                        # Filter out the last used template if possible
                        available_templates = [t for t in templates if t['template_id'] != last_template_id]
                        if available_templates:
                            template = random.choice(available_templates)
                        else:
                            # Fallback if only one template available
                            template = random.choice(templates)
                    else:
                        # First send or only one template available
                        template = random.choice(templates)
                    
                    template_id = template['template_id']
                    template_name = template.get('template_name', f'Template {template_id}')
                    template_text = template['template_text']
                    last_template_id = template_id  # Track for next iteration
                    
                    # Track template usage for reporting
                    template_usage_tracker[template_id] = template_usage_tracker.get(template_id, 0) + 1
                    
                    # Log template selection for verification
                    print(f"   📝 Template ID {template_id} ({template_name}) selected for Lead {lead_id}")
                    
                    # Render template with lead data
                    message_body = render_template(
                        template_text,
                        name=lead_name,
                        store_name=store_name,
                        city=lead_city,
                        state=lead_state
                    )
                    
                    # Send SMS via Twilio
                    message = twilio_client.messages.create(
                        body=message_body,
                        from_=from_phone,
                        to=to_phone
                    )
                    
                    # Update lead's sms_consent_requested_at timestamp and track sender number
                    cursor.execute("""
                        UPDATE OutboundLeads
                        SET sms_consent_requested_at = GETDATE(),
                            sms_from_number = ?
                        WHERE lead_id = ?
                    """, (from_phone, lead_id))
                    conn.commit()
                    
                    # Increment template usage count
                    cursor.execute("""
                        UPDATE sms_templates
                        SET usage_count = usage_count + 1
                        WHERE template_id = ?
                    """, template['template_id'])
                    conn.commit()
                    
                    # Track successful send in PhoneStatus (Milestone 2)
                    try:
                        from services.phone_status_service import get_phone_status_service
                        phone_status_service = get_phone_status_service()
                        phone_status_service.repository.create_or_update(to_phone, {
                            'last_sms_status': 'sent',
                            'last_error_code': None
                        })
                    except Exception as ps_error:
                        # Don't fail if PhoneStatus update fails
                        print(f"   ⚠️  Warning: Failed to update PhoneStatus: {ps_error}")
                    
                    # Update batch_lead_mapping with success status
                    try:
                        cursor.execute("""
                            UPDATE batch_lead_mapping
                            SET status = 'sent', sent_at = GETDATE()
                            WHERE batch_id = ? AND lead_id = ?
                        """, (batch_id, lead_id))
                        conn.commit()
                    except Exception as mapping_error:
                        print(f"   ⚠️  Warning: Failed to update batch_lead_mapping: {mapping_error}")
                    
                    sent_count += 1
                    print(f"✅ SMS sent to Lead {lead_id} ({to_phone}) from {from_phone}")
                    
                except TwilioRestException as e:
                    # Enhanced error logging with more context
                    error_details = {
                        'lead_id': lead_id,
                        'phone_number': to_phone,
                        'from_number': from_phone,
                        'error': str(e.msg),
                        'error_code': e.code,
                        'twilio_error_code': getattr(e, 'code', None)
                    }
                    
                    # Special handling for common Twilio errors
                    if e.code == 21266:
                        error_details['error'] = f"Twilio Error 21266: The 'From' phone number ({from_phone}) is not a valid, SMS-capable Twilio phone number for your account. Verify the number is active and SMS-enabled in Twilio."
                    elif e.code == 21211:
                        error_details['error'] = f"Twilio Error 21211: Invalid 'To' phone number ({to_phone}). Number may be invalid or not SMS-capable."
                    elif e.code == 21610:
                        error_details['error'] = f"Twilio Error 21610: Unsubscribed recipient. The number {to_phone} has replied STOP and cannot receive messages."
                    elif e.code == 30003:
                        error_details['error'] = f"Twilio Error 30003: Unreachable destination handset. Phone may be off or out of service area."
                    
                    # Check if this error is retryable (e.g., 30003 = unreachable handset)
                    if e.code in RETRYABLE_ERROR_CODES:
                        # Add to retry queue for later attempt
                        retry_queue.append({
                            'lead_row': lead_row,
                            'error_code': e.code,
                            'attempt_count': 1,
                            'from_phone': from_phone,
                            'twilio_number_id': twilio_number_id
                        })
                        print(f"🔄 Lead {lead_id} ({to_phone}) added to retry queue (Error {e.code})")
                    
                    # Track error in PhoneStatus (Milestone 2)
                    try:
                        from services.phone_status_service import get_phone_status_service
                        phone_status_service = get_phone_status_service()
                        
                        # Track error codes: 30003, 30005, 30006, 30007, 21610
                        error_code_to_track = None
                        if e.code in [30003, 30005, 30006, 30007, 21610]:
                            error_code_to_track = e.code
                            phone_status_service.track_error(to_phone, error_code_to_track)
                            print(f"   📊 Error tracked in PhoneStatus: {error_code_to_track}")
                            
                            # For 21610 (unsubscribed), also mark as opted out
                            if e.code == 21610:
                                phone_status_service.set_opted_out(to_phone)
                                print(f"   🚫 PhoneStatus: Marked {to_phone} as opted out")
                            
                            # For 30005 (invalid) and 30006 (landline), mark as hard bounce
                            if e.code in [30005, 30006]:
                                reason = 'invalid_number' if e.code == 30005 else 'landline'
                                phone_status_service.set_hard_bounce(to_phone, reason)
                                print(f"   🚫 PhoneStatus: Marked {to_phone} as hard bounce ({reason})")
                    except Exception as ps_error:
                        print(f"   ⚠️  Warning: Failed to track error in PhoneStatus: {ps_error}")
                        # Don't fail the whole process if PhoneStatus tracking fails
                    
                    errors.append(error_details)
                    
                    # Update batch_lead_mapping with failure status
                    try:
                        cursor.execute("""
                            UPDATE batch_lead_mapping
                            SET status = 'failed', error_code = ?, error_message = ?
                            WHERE batch_id = ? AND lead_id = ?
                        """, (e.code, error_details['error'][:500], batch_id, lead_id))
                        conn.commit()
                    except Exception as mapping_error:
                        print(f"   ⚠️  Warning: Failed to update batch_lead_mapping: {mapping_error}")
                    
                    failed_count += 1
                    print(f"❌ Twilio Error for Lead {lead_id} ({to_phone}): Code {e.code} - {e.msg}")
                
                except Exception as e:
                    error_msg = str(e)[:500]
                    errors.append({
                        'lead_id': lead_id,
                        'phone_number': to_phone,
                        'error': error_msg
                    })
                    
                    # Update batch_lead_mapping with failure status
                    try:
                        cursor.execute("""
                            UPDATE batch_lead_mapping
                            SET status = 'failed', error_message = ?
                            WHERE batch_id = ? AND lead_id = ?
                        """, (error_msg, batch_id, lead_id))
                        conn.commit()
                    except Exception as mapping_error:
                        print(f"   ⚠️  Warning: Failed to update batch_lead_mapping: {mapping_error}")
                    
                    failed_count += 1
                
                # Rate limiting: Use configurable interval (default 5 minutes = 300 seconds)
                # This helps avoid carrier spam detection and ensures compliance
                sms_interval = config.campaign.SMS_SEND_INTERVAL_SECONDS
                if idx < lead_count:  # Don't wait after last message
                    interval_minutes = sms_interval // 60
                    print(f"   ⏳ Waiting {interval_minutes} minute(s) before next SMS ({idx}/{lead_count})...")
                    await asyncio.sleep(sms_interval)
            
            print(f"\n{'='*70}")
            print(f"SMS sending completed (initial pass):")
            print(f"   Successfully sent: {sent_count}/{lead_count}")
            print(f"   Failed: {failed_count}/{lead_count}")
            print(f"   In retry queue: {len(retry_queue)}")
            
            # ================================================================
            # STEP 5.5: Process retry queue for temporarily failed leads
            # ================================================================
            retry_sent_count = 0
            retry_failed_count = 0
            
            if retry_queue:
                print(f"\n{'='*70}")
                print(f"🔄 RETRY QUEUE: Processing {len(retry_queue)} failed lead(s)...")
                print(f"   Waiting {RETRY_DELAY_SECONDS} seconds before retry...")
                print(f"{'='*70}")
                time.sleep(RETRY_DELAY_SECONDS)
                
                for retry_item in retry_queue:
                    retry_lead_row = retry_item['lead_row']
                    retry_attempt = retry_item['attempt_count']
                    retry_from_phone = retry_item['from_phone']
                    retry_twilio_number_id = retry_item['twilio_number_id']
                    
                    retry_lead_id = retry_lead_row[0]
                    retry_to_phone = retry_lead_row[1]
                    retry_lead_name = retry_lead_row[2] or "there"
                    retry_lead_city = retry_lead_row[3] or ""
                    retry_lead_state = retry_lead_row[4] or ""
                    
                    if retry_attempt >= MAX_RETRY_ATTEMPTS:
                        print(f"   ⏭️ Lead {retry_lead_id} ({retry_to_phone}): Max retries ({MAX_RETRY_ATTEMPTS}) reached, skipping")
                        continue
                    
                    print(f"   🔄 Retry attempt {retry_attempt + 1}/{MAX_RETRY_ATTEMPTS} for Lead {retry_lead_id} ({retry_to_phone})")
                    
                    try:
                        # Select random template
                        template = random.choice(templates)
                        template_text = template['template_text']
                        
                        # Render template
                        message_body = render_template(
                            template_text,
                            name=retry_lead_name,
                            store_name=store_name,
                            city=retry_lead_city,
                            state=retry_lead_state
                        )
                        
                        # Send SMS
                        message = twilio_client.messages.create(
                            body=message_body,
                            from_=retry_from_phone,
                            to=retry_to_phone
                        )
                        
                        # Update lead's sms_consent_requested_at
                        cursor.execute("""
                            UPDATE OutboundLeads
                            SET sms_consent_requested_at = GETDATE(),
                                sms_from_number = ?
                            WHERE lead_id = ?
                        """, (retry_from_phone, retry_lead_id))
                        conn.commit()
                        
                        retry_sent_count += 1
                        sent_count += 1
                        failed_count -= 1  # Remove from failed count since it succeeded on retry
                        
                        # Remove from errors list
                        errors[:] = [e for e in errors if e.get('lead_id') != retry_lead_id]
                        
                        print(f"   ✅ RETRY SUCCESS: Lead {retry_lead_id} ({retry_to_phone})")
                        
                    except TwilioRestException as e:
                        retry_failed_count += 1
                        print(f"   ❌ RETRY FAILED: Lead {retry_lead_id} ({retry_to_phone}): {e.code} - {e.msg}")
                    except Exception as e:
                        retry_failed_count += 1
                        print(f"   ❌ RETRY FAILED: Lead {retry_lead_id} ({retry_to_phone}): {str(e)}")
                    
                    # Anti-spam delay between retries
                    time.sleep(random.uniform(SMS_SEND_DELAY_MIN, SMS_SEND_DELAY_MAX))
                
                print(f"\n   Retry results: {retry_sent_count} succeeded, {retry_failed_count} still failed")
            
            print(f"\n{'='*70}")
            print(f"FINAL SMS sending results:")
            print(f"   Successfully sent: {sent_count}/{lead_count}")
            print(f"   Failed: {failed_count}/{lead_count}")
            
            # Display template usage distribution
            if template_usage_tracker:
                print(f"\n   Template usage distribution:")
                for template_id, count in sorted(template_usage_tracker.items()):
                    template_name = next((t.get('template_name', f'Template {template_id}') for t in templates if t['template_id'] == template_id), f'Template {template_id}')
                    percentage = (count / sent_count * 100) if sent_count > 0 else 0
                    print(f"      Template ID {template_id} ({template_name}): {count} times ({percentage:.1f}%)")
            
            print(f"{'='*70}\n")
            
            # Note: Phone number counters are updated per SMS above, not in batch here
            print(f"✅ Phone number counters updated during sending")
            
            # ================================================================
            # STEP 7: Update batch status
            # ================================================================
            print(f"\n[Batch Executor] Updating batch status...")
            error_message = None
            if errors:
                error_message = f"{failed_count} SMS failed. First error: {errors[0]['error']}"
            
            cursor.execute("""
                UPDATE sms_batches
                SET 
                    actual_sent = ?,
                    status = 'completed',
                    completed_at = GETDATE(),
                    error_message = ?
                WHERE batch_id = ?
            """, sent_count, error_message, batch_id)
            conn.commit()
            
            # ================================================================
            # STEP 8: Update campaign actual_sent count and status
            # ================================================================
            cursor.execute("""
                UPDATE sms_campaigns
                SET actual_sent = actual_sent + ?,
                    status = CASE 
                        WHEN status = 'pending' THEN 'active'
                        ELSE status
                    END
                WHERE campaign_id = ?
            """, sent_count, campaign_id)
            conn.commit()
            
            # Check if all batches are completed and mark campaign as completed
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_batches,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_batches
                FROM sms_batches
                WHERE campaign_id = ?
            """, campaign_id)
            batch_status = cursor.fetchone()
            
            if batch_status and batch_status[0] > 0 and batch_status[0] == batch_status[1]:
                # All batches completed - mark campaign as completed
                cursor.execute("""
                    UPDATE sms_campaigns
                    SET status = 'completed',
                        completed_at = GETDATE()
                    WHERE campaign_id = ?
                """, campaign_id)
                conn.commit()
                print(f"✅ Campaign {campaign_id} marked as COMPLETED (all {batch_status[0]} batches done)")
            
            # Calculate duration
            duration_seconds = time.time() - start_time
            
            # ================================================================
            # STEP 9: Return execution summary
            # ================================================================
            result = {
                'batch_id': batch_id,
                'campaign_id': campaign_id,
                'batch_number': batch_number,
                'store_id': store_id,
                'store_name': store_name,
                'phone_number_used': from_phone,
                'twilio_number_id': twilio_number_id,
                'target_count': target_count,
                'actual_sent': sent_count,
                'failed_count': failed_count,
                'errors': errors,
                'duration_seconds': round(duration_seconds, 2),
                'status': 'completed'
            }
            
            
            # Broadcast campaign progress update with TOTAL campaign stats
            try:
                from services.websocket_service import broadcast_event_sync, EventType
                
                # Get updated campaign totals from database
                cursor.execute("""
                    SELECT 
                        c.target_count,
                        c.actual_sent,
                        c.status,
                        COUNT(b.batch_id) as total_batches,
                        SUM(CASE WHEN b.status = 'completed' THEN 1 ELSE 0 END) as completed_batches,
                        SUM(CASE WHEN b.status = 'pending' THEN 1 ELSE 0 END) as pending_batches
                    FROM sms_campaigns c
                    LEFT JOIN sms_batches b ON c.campaign_id = b.campaign_id
                    WHERE c.campaign_id = ?
                    GROUP BY c.target_count, c.actual_sent, c.status
                """, campaign_id)
                campaign_stats = cursor.fetchone()
                
                campaign_target = campaign_stats[0] if campaign_stats else target_count
                campaign_actual_sent = campaign_stats[1] if campaign_stats else sent_count
                campaign_status = campaign_stats[2] if campaign_stats else 'active'
                total_batches = campaign_stats[3] if campaign_stats else 1
                completed_batches = campaign_stats[4] if campaign_stats else 1
                pending_batches = campaign_stats[5] if campaign_stats else 0
                
                # Calculate failed count (target - actual sent)
                campaign_failed = campaign_target - campaign_actual_sent
                progress_percentage = round((campaign_actual_sent / campaign_target * 100), 1) if campaign_target > 0 else 0
                
                broadcast_event_sync(
                    EventType.CAMPAIGN_PROGRESS,
                    {
                        "batch_id": batch_id,
                        "campaign_id": campaign_id,
                        "store_id": store_id,
                        "batch_status": "completed",
                        "batch_sent": sent_count,
                        "batch_failed": failed_count,
                        # Campaign totals for real-time UI update
                        "campaign_status": campaign_status,
                        "campaign_target": campaign_target,
                        "campaign_actual_sent": campaign_actual_sent,
                        "campaign_failed": campaign_failed,
                        "progress_percentage": progress_percentage,
                        "total_batches": total_batches,
                        "completed_batches": completed_batches,
                        "pending_batches": pending_batches
                    }
                )
                print(f"📡 Broadcasted campaign progress: {campaign_actual_sent}/{campaign_target} ({progress_percentage}%)")
            except Exception as e:
                print(f"[Batch Executor] WARNING: Failed to broadcast campaign progress: {e}")
            print(f"SMS sent: {sent_count}/{target_count}")
            print(f"Failed: {failed_count}")
            print(f"Duration: {duration_seconds:.2f} seconds")
            print(f"{'='*70}\n")
            
            return result
        
        except Exception as e:
            # Mark batch as failed
            try:
                cursor.execute("""
                    UPDATE sms_batches
                    SET 
                        status = 'failed',
                        error_message = ?,
                        completed_at = GETDATE()
                    WHERE batch_id = ?
                """, str(e), batch_id)
                conn.commit()
            except:
                pass
            
            print(f"\n❌ Batch execution failed: {e}")
            raise
        
        finally:
            cursor.close()
            conn.close()


if __name__ == "__main__":
    """Quick test of campaign manager."""
    print("=" * 70)
    print("SMS Campaign Manager - Quick Test")
    print("=" * 70)
    
    manager = SMSCampaignManager()
    
    # Test: Create a small campaign
    print("\n[TEST] Creating campaign for store_id=1 with 50 leads...")
    try:
        result = manager.create_campaign(
            store_id=1,
            target_count=50,
            start_time=datetime.now() + timedelta(minutes=30)
        )
        
        print(f"\n✅ Campaign created successfully!")
        print(f"   Campaign ID: {result['campaign_id']}")
        print(f"   Batches: {result['batch_count']}")
        print(f"   Cost: ${result['estimated_cost']}")
        print(f"   SMS Sent: {result['sms_sent']}")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
    
    print("\n" + "=" * 70)
