#!/usr/bin/env python3
"""
Consent Tracker - SMS Reply Classification and Processing
Handles incoming SMS replies from leads and updates consent status.

Key Features:
1. Classifies replies as YES, STOP, or OTHER
2. Updates lead consent status in database
3. Sends auto-reply messages
4. Logs all replies for audit trail
5. Idempotent (handles duplicate Twilio webhooks)

Reply Classification:
- YES: Consent granted → mark lead as sms_verified=true
- STOP: Opt-out request → mark lead as dnc_flag=true  
- OTHER: Unrecognized → log for manual review

Database Tables Used:
- OutboundLeads: Lead consent status updates
- sms_replies: Audit trail of all incoming SMS
"""

import os
import sys
import pyodbc
import re
from datetime import datetime
from typing import Optional, Dict, Literal
from dotenv import load_dotenv
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

load_dotenv()

# SQL Server configuration
SQL_SERVER = os.getenv('SQLServer')
SQL_USER = os.getenv('SQLUser')
SQL_PASSWORD = os.getenv('SQLPassword')
SQL_DATABASE = os.getenv('SQLDatabase')

# Twilio configuration
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')


# Reply classification keyword lists
YES_KEYWORDS = [
    'yes', 'yeah', 'yea', 'yep', 'sure', 'ok', 'okay', 'k',
    'interested', 'call me', 'call', 'contact me', 'reach out',
    'sounds good', 'that works', 'perfect', 'great', 'absolutely',
    'definitely', 'confirm', 'confirmed', 'accept', 'agree',
    'si', 'sí'  # Spanish
]

STOP_KEYWORDS = [
    'stop', 'unsubscribe', 'remove', 'no', 'nope', 'nah',
    "don't", 'dont', 'never', 'leave me alone', 'not interested',
    'remove me', 'take me off', 'delete', 'cancel', 'quit',
    'end', 'opt out', 'optout', 'opt-out', 'do not contact',
    'do not call', "don't call", 'dont call', 'no thanks'
]


class ConsentTracker:
    """
    Tracks and processes SMS consent replies from leads.
    
    Main Functions:
    1. classify_reply(body) -> "YES" | "STOP" | "OTHER"
    2. process_reply(from_number, body, twilio_sid) -> Dict with results
    3. send_auto_reply(to_number, reply_type) -> bool
    
    Usage:
        tracker = ConsentTracker()
        
        # Classify a reply
        classification = tracker.classify_reply("YES please call me")
        # Returns: "YES"
        
        # Process a complete reply (from Twilio webhook)
        result = tracker.process_reply(
            from_number="+15551234567",
            body="YES",
            twilio_message_sid="SM1234...",
            from_phone_number="+15559876543"
        )
        
        # Result:
        # {
        #     'classification': 'YES',
        #     'lead_updated': True,
        #     'auto_reply_sent': True,
        #     'duplicate': False
        # }
    """
    
    # Auto-reply message templates
    AUTO_REPLY_YES = (
        "Thanks for confirming! We'll give you a call soon to discuss your options. "
        "Reply STOP anytime to opt out."
    )
    
    AUTO_REPLY_STOP = (
        "You've been removed from our contact list. We won't reach out again. "
        "Thank you."
    )
    
    AUTO_REPLY_OTHER = (
        "Thanks for your message! Reply YES to confirm we can call you, or STOP to opt out."
    )
    
    def __init__(self):
        """Initialize the consent tracker."""
        self.connection_string = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={SQL_SERVER};"
            f"DATABASE={SQL_DATABASE};"
            f"UID={SQL_USER};"
            f"PWD={SQL_PASSWORD}"
        )
        
        # Initialize Twilio client
        if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
            self.twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        else:
            self.twilio_client = None
            print("⚠️  Twilio credentials not configured. Auto-replies disabled.")
    
    def get_db_connection(self):
        """Get database connection."""
        return pyodbc.connect(self.connection_string)
    
    def classify_reply(self, body: str) -> Literal["YES", "STOP", "OTHER"]:
        """
        Classify SMS reply into YES, STOP, or OTHER.
        
        Classification Logic:
        1. Normalize text: lowercase, remove punctuation
        2. Check for STOP keywords first (higher priority for compliance)
        3. Check for YES keywords
        4. Default to OTHER if no match
        
        Args:
            body: SMS message body (string)
        
        Returns:
            "YES" | "STOP" | "OTHER"
        
        Examples:
            >>> tracker.classify_reply("YES please!")
            "YES"
            
            >>> tracker.classify_reply("STOP calling me")
            "STOP"
            
            >>> tracker.classify_reply("Who is this?")
            "OTHER"
        """
        if not body or not isinstance(body, str):
            return "OTHER"
        
        # Normalize: lowercase, keep only alphanumeric and spaces
        normalized = re.sub(r'[^a-z0-9\s]', '', body.lower().strip())
        
        # Split into words
        words = normalized.split()
        
        # Check for STOP keywords first (compliance priority)
        for keyword in STOP_KEYWORDS:
            keyword_words = keyword.split()
            if len(keyword_words) == 1:
                # Single word match
                if keyword in words:
                    return "STOP"
            else:
                # Multi-word phrase match
                if keyword in normalized:
                    return "STOP"
        
        # Check for YES keywords
        for keyword in YES_KEYWORDS:
            keyword_words = keyword.split()
            if len(keyword_words) == 1:
                # Single word match
                if keyword in words:
                    return "YES"
            else:
                # Multi-word phrase match
                if keyword in normalized:
                    return "YES"
        
        # Default to OTHER
        return "OTHER"
    
    def process_reply(
        self,
        from_number: str,
        body: str,
        twilio_message_sid: str,
        from_phone_number: str,
        received_at: Optional[datetime] = None
    ) -> Dict:
        """
        Process an incoming SMS reply from a lead.
        
        Complete Workflow:
        1. Check for duplicate (idempotency via MessageSid)
        2. Classify reply (YES/STOP/OTHER)
        3. Find lead by phone number
        4. Update lead status based on classification
        5. Log reply to sms_replies table
        6. Send auto-reply message
        7. Return results
        
        Args:
            from_number: Lead's phone number (E.164 format)
            body: SMS message body
            twilio_message_sid: Twilio MessageSid (for idempotency)
            from_phone_number: Our Twilio number that received the SMS
            received_at: Timestamp (default: now)
        
        Returns:
            Dict with processing results:
            {
                'classification': 'YES' | 'STOP' | 'OTHER',
                'lead_id': int or None,
                'lead_updated': bool,
                'auto_reply_sent': bool,
                'duplicate': bool,
                'error': str or None
            }
        """
        if received_at is None:
            received_at = datetime.now()
        
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        result = {
            'classification': None,
            'lead_id': None,
            'lead_updated': False,
            'auto_reply_sent': False,
            'duplicate': False,
            'error': None
        }
        
        try:
            print(f"\n{'='*70}")
            print(f"[Consent Tracker] Processing SMS Reply")
            print(f"{'='*70}")
            print(f"From: {from_number}")
            print(f"To: {from_phone_number}")
            print(f"Body: {body}")
            print(f"Twilio SID: {twilio_message_sid}")
            
            # ================================================================
            # STEP 1: Check for duplicate (idempotency)
            # ================================================================
            print(f"\n[Step 1] Checking for duplicate MessageSid...")
            cursor.execute("""
                SELECT reply_id, classification
                FROM sms_replies
                WHERE twilio_message_sid = ?
            """, twilio_message_sid)
            
            existing_reply = cursor.fetchone()
            if existing_reply:
                print(f"⚠️  Duplicate webhook detected. MessageSid already processed: {twilio_message_sid}")
                result['duplicate'] = True
                result['classification'] = existing_reply[1]
                return result
            
            print(f"✅ Not a duplicate. Proceeding...")
            
            # ================================================================
            # STEP 2: Classify reply
            # ================================================================
            print(f"\n[Step 2] Classifying reply...")
            classification = self.classify_reply(body)
            result['classification'] = classification
            print(f"✅ Classification: {classification}")
            
            # ================================================================
            # STEP 3: Find lead by phone number
            # ================================================================
            print(f"\n[Step 3] Finding lead by phone number...")
            
            # Normalize phone number for matching
            normalized_from = self._normalize_phone(from_number)
            
            cursor.execute("""
                SELECT lead_id, name, sms_verified, dnc_flag, sms_from_number
                FROM OutboundLeads
                WHERE phone_number = ?
            """, normalized_from)
            
            lead_row = cursor.fetchone()
            if not lead_row:
                print(f"⚠️  Lead not found for phone number: {normalized_from}")
                result['error'] = f"Lead not found: {normalized_from}"
                
                # Still log the reply for audit
                self._log_reply(
                    cursor=cursor,
                    from_number=normalized_from,
                    to_number=from_phone_number,
                    body=body,
                    classification=classification,
                    twilio_message_sid=twilio_message_sid,
                    lead_id=None,
                    received_at=received_at
                )
                
                # Also log to SMSConversations (even without lead_id for unknown numbers)
                try:
                    message_type = 'consent_reply'
                    if classification == 'YES':
                        message_type = 'consent_yes'
                    elif classification == 'STOP':
                        message_type = 'consent_stop'
                    else:
                        message_type = 'consent_other'
                    
                    cursor.execute("""
                        INSERT INTO SMSConversations (lead_id, phone_number, message_type, message_content, twilio_sid, direction, created_at)
                        VALUES (?, ?, ?, ?, ?, 'inbound', ?)
                    """, (None, normalized_from, message_type, body, twilio_message_sid, received_at))
                    print(f"✅ Reply logged to SMSConversations (inbound, no lead)")
                except Exception as e:
                    print(f"⚠️  Warning: Failed to log to SMSConversations: {e}")
                
                conn.commit()
                
                # Still send auto-reply
                result['auto_reply_sent'] = self._send_auto_reply(
                    to_number=normalized_from,
                    from_number=from_phone_number,
                    reply_type=classification
                )
                
                return result
            
            lead_id = lead_row[0]
            lead_name = lead_row[1] or "Unknown"
            sms_from_number = lead_row[4]  # The number that sent SMS to this lead (index 4, not 5)
            result['lead_id'] = lead_id
            result['sms_from_number'] = sms_from_number
            
            print(f"✅ Lead found: {lead_name} (ID: {lead_id})")
            if sms_from_number:
                print(f"   SMS was sent from: {sms_from_number}")
            
            # ================================================================
            # STEP 4: Update lead status based on classification
            # ================================================================
            print(f"\n[Step 4] Updating lead status...")
            
            if classification == "YES":
                # Check if this is a new verification (wasn't verified before)
                current_verified = lead_row[2]  # sms_verified from SELECT query
                is_new_verification = (current_verified == 0 or current_verified is None)
                
                # Consent granted
                cursor.execute("""
                    UPDATE OutboundLeads
                    SET 
                        sms_verified = 1,
                        sms_verified_at = ?
                    WHERE lead_id = ?
                """, received_at, lead_id)
                
                print(f"✅ Lead marked as CONSENTED (sms_verified=1)")
                result['lead_updated'] = True
                
                # ============================================================
                # STEP 4a: Create popup card for manual dialing (if new verification)
                # ============================================================
                if is_new_verification:
                    print(f"\n[Step 4a] Creating popup card for newly verified lead...")
                    
                    # Check if popup already exists for this lead
                    cursor.execute("""
                        SELECT popup_id 
                        FROM PopupQueue 
                        WHERE lead_id = ? AND status = 'pending'
                    """, (lead_id,))
                    
                    existing_popup = cursor.fetchone()
                    if existing_popup:
                        print(f"⚠️  Popup already exists for lead {lead_id} (popup_id: {existing_popup[0]})")
                    else:
                        # Create new popup card
                        cursor.execute("""
                            INSERT INTO PopupQueue (lead_id, status, created_at)
                            VALUES (?, 'pending', ?)
                        """, (lead_id, received_at))
                        
                        popup_id = cursor.execute("SELECT @@IDENTITY").fetchone()[0]
                        print(f"✅ Created popup card (popup_id: {popup_id}) for lead {lead_id} (YES reply received)")
                else:
                    print(f"ℹ️  Lead was already verified. No new popup card needed.")
            
            elif classification == "STOP":
                # Opt-out / DNC
                cursor.execute("""
                    UPDATE OutboundLeads
                    SET 
                        dnc_flag = 1
                    WHERE lead_id = ?
                """, lead_id)
                
                print(f"✅ Lead marked as DNC (dnc_flag=1)")
                result['lead_updated'] = True
                
                # Update PhoneStatus to mark as opted out (Milestone 2)
                try:
                    from services.phone_status_service import get_phone_status_service
                    phone_status_service = get_phone_status_service()
                    phone_status_service.set_opted_out(normalized_from)
                    print(f"✅ PhoneStatus updated: Marked {normalized_from} as opted out")
                except Exception as ps_error:
                    print(f"⚠️  Warning: Failed to update PhoneStatus: {ps_error}")
                    # Don't fail the whole process if PhoneStatus update fails
            
            else:
                # OTHER - just log the reply, no status change
                # No need to update OutboundLeads - reply is logged in sms_replies table
                print(f"ℹ️  Reply logged as OTHER. No status change for lead.")
                result['lead_updated'] = False
            
            # ================================================================
            # STEP 5: Log reply to sms_replies table (audit trail)
            # ================================================================
            print(f"\n[Step 5] Logging reply to audit table...")
            self._log_reply(
                cursor=cursor,
                from_number=normalized_from,
                to_number=from_phone_number,
                body=body,
                classification=classification,
                twilio_message_sid=twilio_message_sid,
                lead_id=lead_id,
                received_at=received_at
            )
            print(f"✅ Reply logged to sms_replies table")
            
            # ================================================================
            # STEP 5a: Also log to SMSConversations table (for SMS page display)
            # ================================================================
            print(f"\n[Step 5a] Logging reply to SMSConversations table...")
            try:
                # Determine message type based on classification
                message_type = 'consent_reply'
                if classification == 'YES':
                    message_type = 'consent_yes'
                elif classification == 'STOP':
                    message_type = 'consent_stop'
                else:
                    message_type = 'consent_other'
                
                cursor.execute("""
                    INSERT INTO SMSConversations (lead_id, phone_number, message_type, message_content, twilio_sid, direction, created_at)
                    VALUES (?, ?, ?, ?, ?, 'inbound', ?)
                """, (lead_id, normalized_from, message_type, body, twilio_message_sid, received_at))
                
                print(f"✅ Reply logged to SMSConversations table (inbound)")
                
                # Broadcast SMS received event via WebSocket
                try:
                    from services.websocket_service import broadcast_event_sync, EventType
                    broadcast_event_sync(
                        EventType.SMS_RECEIVED,
                        {
                            "lead_id": lead_id,
                            "phone_number": normalized_from,
                            "message_type": message_type,
                            "message_content": body,
                            "twilio_sid": twilio_message_sid
                        }
                    )
                    print(f"✅ SMS_RECEIVED event broadcasted via WebSocket")
                except Exception as ws_error:
                    print(f"⚠️  Warning: Failed to broadcast SMS_RECEIVED event: {ws_error}")
                    # Don't fail the whole process if broadcast fails
            except Exception as e:
                # Don't fail the whole process if SMSConversations insert fails
                print(f"⚠️  Warning: Failed to log to SMSConversations: {e}")
                # Continue - sms_replies table already has the audit trail
            
            # ================================================================
            # STEP 6: Commit transaction
            # ================================================================
            conn.commit()
            print(f"✅ Database transaction committed")
            
            # ================================================================
            # STEP 7: Send auto-reply
            # ================================================================
            print(f"\n[Step 6] Sending auto-reply...")
            result['auto_reply_sent'] = self._send_auto_reply(
                to_number=normalized_from,
                from_number=from_phone_number,
                reply_type=classification,
                callback_number=sms_from_number  # Tell customer which number will call
            )
            
            if result['auto_reply_sent']:
                print(f"✅ Auto-reply sent successfully")
            else:
                print(f"⚠️  Auto-reply failed (check Twilio credentials)")
            
            # ================================================================
            # STEP 8: Return results
            # ================================================================
            print(f"\n{'='*70}")
            print(f"✅ SMS REPLY PROCESSED SUCCESSFULLY")
            print(f"{'='*70}")
            print(f"Lead ID: {lead_id}")
            print(f"Lead Name: {lead_name}")
            print(f"Classification: {classification}")
            print(f"Lead Updated: {result['lead_updated']}")
            print(f"Auto-Reply Sent: {result['auto_reply_sent']}")
            print(f"{'='*70}\n")
            
            return result
        
        except Exception as e:
            conn.rollback()
            print(f"\n❌ Error processing reply: {e}")
            result['error'] = str(e)
            return result
        
        finally:
            cursor.close()
            conn.close()
    
    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number to E.164 format (+1XXXXXXXXXX)."""
        if not phone:
            return ""
        
        # Remove all non-digit characters
        digits = ''.join(filter(str.isdigit, phone))
        
        # Add +1 prefix if needed
        if len(digits) == 11 and digits.startswith('1'):
            return f"+{digits}"
        elif len(digits) == 10:
            return f"+1{digits}"
        else:
            return f"+{digits}"  # Return as-is with + prefix
    
    def _log_reply(
        self,
        cursor,
        from_number: str,
        to_number: str,
        body: str,
        classification: str,
        twilio_message_sid: str,
        lead_id: Optional[int],
        received_at: datetime
    ):
        """Log SMS reply to sms_replies audit table."""
        cursor.execute("""
            INSERT INTO sms_replies (
                lead_id,
                from_number,
                to_number,
                body,
                classification,
                twilio_message_sid,
                received_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, lead_id, from_number, to_number, body, classification, twilio_message_sid, received_at)
    
    def _send_auto_reply(
        self,
        to_number: str,
        from_number: str,
        reply_type: Literal["YES", "STOP", "OTHER"],
        callback_number: str = None
    ) -> bool:
        """
        Send auto-reply SMS to lead.
        
        Args:
            to_number: Lead's phone number
            from_number: Our Twilio number
            reply_type: Classification type
            callback_number: The number that will call them (for YES replies)
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.twilio_client:
            print(f"⚠️  Twilio client not initialized. Skipping auto-reply.")
            return False
        
        # Select appropriate message
        if reply_type == "YES":
            # Include callback number if available
            if callback_number:
                message_body = (
                    f"Thanks for confirming! We'll give you a call soon from {callback_number} "
                    f"to discuss your options. Reply STOP anytime to opt out."
                )
            else:
                message_body = self.AUTO_REPLY_YES
        elif reply_type == "STOP":
            message_body = self.AUTO_REPLY_STOP
        else:
            message_body = self.AUTO_REPLY_OTHER
        
        try:
            message = self.twilio_client.messages.create(
                body=message_body,
                from_=from_number,
                to=to_number
            )
            
            print(f"✅ Auto-reply sent: {message.sid}")
            return True
        
        except TwilioRestException as e:
            print(f"❌ Twilio error sending auto-reply: {e.msg} (code: {e.code})")
            return False
        
        except Exception as e:
            print(f"❌ Error sending auto-reply: {e}")
            return False
    
    def get_reply_statistics(self, days: int = 7) -> Dict:
        """
        Get SMS reply statistics for the last N days.
        
        Args:
            days: Number of days to look back (default: 7)
        
        Returns:
            Dict with statistics:
            {
                'total_replies': int,
                'yes_count': int,
                'stop_count': int,
                'other_count': int,
                'yes_percentage': float,
                'stop_percentage': float,
                'unique_leads': int
            }
        """
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_replies,
                    SUM(CASE WHEN classification = 'YES' THEN 1 ELSE 0 END) as yes_count,
                    SUM(CASE WHEN classification = 'STOP' THEN 1 ELSE 0 END) as stop_count,
                    SUM(CASE WHEN classification = 'OTHER' THEN 1 ELSE 0 END) as other_count,
                    COUNT(DISTINCT lead_id) as unique_leads
                FROM sms_replies
                WHERE received_at >= DATEADD(day, -?, GETDATE())
            """, days)
            
            row = cursor.fetchone()
            
            if not row or row[0] == 0:
                return {
                    'total_replies': 0,
                    'yes_count': 0,
                    'stop_count': 0,
                    'other_count': 0,
                    'yes_percentage': 0.0,
                    'stop_percentage': 0.0,
                    'unique_leads': 0
                }
            
            total = row[0]
            yes_count = row[1] or 0
            stop_count = row[2] or 0
            other_count = row[3] or 0
            unique_leads = row[4] or 0
            
            return {
                'total_replies': total,
                'yes_count': yes_count,
                'stop_count': stop_count,
                'other_count': other_count,
                'yes_percentage': round((yes_count / total) * 100, 2) if total > 0 else 0.0,
                'stop_percentage': round((stop_count / total) * 100, 2) if total > 0 else 0.0,
                'unique_leads': unique_leads
            }
        
        finally:
            cursor.close()
            conn.close()


if __name__ == "__main__":
    """Quick test of consent tracker."""
    print("=" * 70)
    print("Consent Tracker - Quick Test")
    print("=" * 70)
    
    tracker = ConsentTracker()
    
    # Test classification
    test_messages = [
        "YES please call me",
        "STOP don't contact me",
        "What is this about?",
        "Sure, sounds good",
        "No thanks",
        "Call me tomorrow",
        "UNSUBSCRIBE"
    ]
    
    print("\n[TEST] Testing reply classification...")
    for msg in test_messages:
        classification = tracker.classify_reply(msg)
        print(f"   '{msg}' → {classification}")
    
    print("\n" + "=" * 70)

