"""
Lead Repository
Handles all database operations for leads.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from .base import BaseRepository
from config import config


class LeadRepository(BaseRepository):
    """Repository for lead data access."""
    
    def get_by_id(self, lead_id: int) -> Optional[Dict[str, Any]]:
        """Get lead by ID."""
        query = """
            SELECT lead_id, name, Address, City, County, State, Zip, phone_number,
                   priority, call_count, dnc_flag, sms_verified, sms_verified_at,
                   sms_consent_requested_at, created_at, last_called, store_id, sms_from_number
            FROM OutboundLeads
            WHERE lead_id = ?
        """
        row = self.execute_query(query, (lead_id,), fetch_one=True)
        return self._row_to_dict(row) if row else None
    
    def get_by_phone(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """Get lead by phone number."""
        query = """
            SELECT lead_id, name, Address, City, County, State, Zip, phone_number,
                   priority, call_count, dnc_flag, sms_verified, sms_verified_at,
                   sms_consent_requested_at, created_at, last_called, store_id, sms_from_number
            FROM OutboundLeads
            WHERE phone_number = ?
        """
        row = self.execute_query(query, (phone_number,), fetch_one=True)
        return self._row_to_dict(row) if row else None
    
    def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
        dnc_only: Optional[bool] = None,
        store_id: Optional[int] = None,
        unassigned_only: bool = False
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        Get all leads with filtering and pagination.
        
        Returns:
            Tuple of (leads, total_count)
        """
        where_clauses = []
        params = []
        
        if dnc_only is not None:
            where_clauses.append("dnc_flag = ?")
            params.append(1 if dnc_only else 0)
        
        if unassigned_only:
            where_clauses.append("(store_id IS NULL OR store_id = 0)")
        elif store_id is not None:
            where_clauses.append("store_id = ?")
            params.append(store_id)
        
        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)
        
        query = f"""
            SELECT lead_id, name, Address, City, County, State, Zip, phone_number,
                   priority, call_count, dnc_flag, sms_verified, sms_verified_at,
                   sms_consent_requested_at, created_at, last_called, store_id, sms_from_number
            FROM OutboundLeads
            {where_sql}
            ORDER BY created_at DESC
        """
        
        results, total = self.paginate(query, params, page=(offset // limit) + 1, page_size=limit)
        
        leads = [self._row_to_dict(row) for row in results]
        return leads, total
    
    def get_next_available(self) -> Optional[Dict[str, Any]]:
        """Get next available lead for calling."""
        query = """
            SELECT TOP 1
                lead_id, name, Address, City, County, State, Zip, phone_number, priority,
                sms_verified, store_id, sms_from_number
            FROM OutboundLeads
            WHERE dnc_flag = 0
              AND sms_verified = 1
              AND (last_called IS NULL OR last_called < CAST(GETDATE() AS DATE))
            ORDER BY 
                CASE WHEN priority IS NOT NULL THEN priority ELSE 999 END ASC,
                created_at ASC
        """
        row = self.execute_query(query, fetch_one=True)
        
        if row:
            # Handle both 11-column (without sms_from_number) and 12-column (with sms_from_number) rows
            row_length = len(row)
            result = {
                "lead_id": row[0],
                "name": row[1],
                "Address": row[2],
                "City": row[3],
                "County": row[4],
                "State": row[5],
                "Zip": row[6],
                "phone_number": row[7],
                "priority": row[8],
                "sms_verified": bool(row[9]),
                "store_id": row[10]
            }
            # Add sms_from_number if present (12th column)
            if row_length > 11:
                result["sms_from_number"] = row[11]
            else:
                result["sms_from_number"] = None
            return result
        return None
    
    def get_multiple(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get multiple available leads for parallel calling."""
        query = f"""
            SELECT TOP {count}
                lead_id, name, Address, City, County, State, Zip, phone_number, priority,
                sms_verified, store_id, sms_from_number
            FROM OutboundLeads
            WHERE dnc_flag = 0
              AND sms_verified = 1
              AND (last_called IS NULL OR last_called < CAST(GETDATE() AS DATE))
            ORDER BY 
                CASE WHEN priority IS NOT NULL THEN priority ELSE 999 END ASC,
                created_at ASC
        """
        rows = self.execute_query(query, fetch_all=True)
        
        return [{
            "lead_id": row[0],
            "name": row[1],
            "Address": row[2],
            "City": row[3],
            "County": row[4],
            "State": row[5],
            "Zip": row[6],
            "phone_number": row[7],
            "priority": row[8],
            "sms_verified": bool(row[9]),
            "store_id": row[10],
            "sms_from_number": row[11] if len(row) > 11 else None
        } for row in rows]
    
    def create(self, lead_data: Dict[str, Any]) -> int:
        """Create a new lead."""
        # Validate phone number if provided (safety check - should already be validated by service layer)
        phone_number = lead_data.get('phone_number')
        if phone_number:
            from utils.phone_validator import validate_us_phone_number
            from core.exceptions import PhoneNumberValidationError
            is_valid, normalized, error = validate_us_phone_number(phone_number)
            if not is_valid:
                raise PhoneNumberValidationError(error or "Invalid phone number format")
            lead_data['phone_number'] = normalized
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO OutboundLeads 
                    (name, Address, City, County, State, Zip, phone_number, priority, 
                     dnc_flag, store_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
                """, (
                    lead_data.get('name'),
                    lead_data.get('Address'),
                    lead_data.get('City'),
                    lead_data.get('County'),
                    lead_data.get('State'),
                    lead_data.get('Zip'),
                    lead_data['phone_number'],
                    lead_data.get('priority', 1),
                    lead_data.get('store_id')
                ))
                
                return self.get_last_insert_id(conn)
            finally:
                cursor.close()
    
    def update(self, lead_id: int, updates: Dict[str, Any]) -> bool:
        """Update an existing lead."""
        # Validate phone number if provided (safety check - should already be validated by service layer)
        if 'phone_number' in updates:
            from utils.phone_validator import validate_us_phone_number
            from core.exceptions import PhoneNumberValidationError
            is_valid, normalized, error = validate_us_phone_number(updates['phone_number'])
            if not is_valid:
                raise PhoneNumberValidationError(error or "Invalid phone number format")
            updates['phone_number'] = normalized
        
        set_clauses = []
        params = []
        
        for key, value in updates.items():
            if key in ['name', 'Address', 'City', 'County', 'State', 'Zip', 
                      'phone_number', 'priority', 'store_id', 'dnc_flag', 'sms_verified', 
                      'sms_consent_requested_at', 'sms_verified_at']:
                set_clauses.append(f"{key} = ?")
                params.append(value)
        
        if not set_clauses:
            return False
        
        params.append(lead_id)
        query = f"UPDATE OutboundLeads SET {', '.join(set_clauses)} WHERE lead_id = ?"
        
        rows_affected = self.execute_non_query(query, tuple(params))
        return rows_affected > 0
    
    def delete(self, lead_id: int) -> bool:
        """
        Delete a lead.
        
        First deletes related records in all tables that reference this lead to avoid foreign key constraint errors.
        
        Tables with foreign key references to OutboundLeads:
        - batch_lead_mapping (must delete first)
        - OutboundCallResults
        - SMSConversations
        - PhotoSubmissions
        - PopupQueue
        - sms_replies (has ON DELETE SET NULL, so handled automatically)
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"[LeadRepo] Deleting lead_id={lead_id} and all related records...")
                
                # Step 1: Delete related records in batch_lead_mapping
                cursor.execute(
                    "DELETE FROM batch_lead_mapping WHERE lead_id = ?",
                    (lead_id,)
                )
                deleted_mappings = cursor.rowcount
                if deleted_mappings > 0:
                    logger.info(f"[LeadRepo] Deleted {deleted_mappings} batch_lead_mapping record(s)")
                
                # Step 2: Delete call results
                cursor.execute(
                    "DELETE FROM OutboundCallResults WHERE lead_id = ?",
                    (lead_id,)
                )
                deleted_calls = cursor.rowcount
                if deleted_calls > 0:
                    logger.info(f"[LeadRepo] Deleted {deleted_calls} call result record(s)")
                
                # Step 3: Delete SMS conversations
                cursor.execute(
                    "DELETE FROM SMSConversations WHERE lead_id = ?",
                    (lead_id,)
                )
                deleted_sms = cursor.rowcount
                if deleted_sms > 0:
                    logger.info(f"[LeadRepo] Deleted {deleted_sms} SMS conversation record(s)")
                
                # Step 4: Delete photo submissions
                cursor.execute(
                    "DELETE FROM PhotoSubmissions WHERE lead_id = ?",
                    (lead_id,)
                )
                deleted_photos = cursor.rowcount
                if deleted_photos > 0:
                    logger.info(f"[LeadRepo] Deleted {deleted_photos} photo submission record(s)")
                
                # Step 5: Delete popup queue entries
                cursor.execute(
                    "DELETE FROM PopupQueue WHERE lead_id = ?",
                    (lead_id,)
                )
                deleted_popups = cursor.rowcount
                if deleted_popups > 0:
                    logger.info(f"[LeadRepo] Deleted {deleted_popups} popup queue record(s)")
                
                # Step 6: Delete the lead itself
                # Note: sms_replies has ON DELETE SET NULL, so it will automatically set lead_id to NULL
                cursor.execute(
                    "DELETE FROM OutboundLeads WHERE lead_id = ?",
                    (lead_id,)
                )
                rows_affected = cursor.rowcount
                
                conn.commit()
                
                if rows_affected > 0:
                    logger.info(f"[LeadRepo] ✅ Successfully deleted lead_id={lead_id} and all related records")
                else:
                    logger.warning(f"[LeadRepo] ⚠️ Lead {lead_id} not found or already deleted")
                
                return rows_affected > 0
            except Exception as e:
                conn.rollback()
                logger.error(f"[LeadRepo] ❌ Error deleting lead_id={lead_id}: {e}")
                raise
            finally:
                cursor.close()
    
    def mark_as_called(self, lead_id: int) -> bool:
        """
        Mark lead as called (update last_called timestamp only).
        
        ⚠️ IMPORTANT: This does NOT increment call_count.
        call_count is incremented in update_lead_after_call() when the call result is saved.
        This prevents double-counting when mark_lead_called() is called before the call
        and save_call_result() is called after the call completes.
        """
        query = """
            UPDATE OutboundLeads
            SET last_called = GETDATE()
            WHERE lead_id = ?
        """
        rows_affected = self.execute_non_query(query, (lead_id,))
        return rows_affected > 0
    
    def mark_as_dnc(self, phone_number: str) -> bool:
        """Mark lead as Do Not Call."""
        query = "UPDATE OutboundLeads SET dnc_flag = 1 WHERE phone_number = ?"
        rows_affected = self.execute_non_query(query, (phone_number,))
        return rows_affected > 0
    
    def exists_by_phone(self, phone_number: str) -> bool:
        """Check if lead exists by phone number."""
        query = "SELECT lead_id FROM OutboundLeads WHERE phone_number = ?"
        return self.exists(query, (phone_number,))
    
    def bulk_assign_to_store(self, lead_ids: List[int], store_id: int) -> int:
        """Bulk assign leads to a store."""
        if not lead_ids:
            return 0
        
        placeholders = ','.join(['?' for _ in lead_ids])
        query = f"""
            UPDATE OutboundLeads
            SET store_id = ?
            WHERE lead_id IN ({placeholders})
        """
        params = [store_id] + lead_ids
        return self.execute_non_query(query, tuple(params))
    
    def count_eligible_for_consent(
        self,
        store_id: Optional[int] = None,
        force: bool = False
    ) -> int:
        """
        Count leads eligible for consent SMS requests.
        
        Eligibility criteria (matching campaign logic):
        - dnc_flag = 0
        - Never sent consent SMS, or consent sent more than cooldown days ago (no duplicate SMS)
        - Not already in a progressing campaign (batch status pending or executing)
        - store_id matches (if provided)
        
        Args:
            store_id: Filter by store ID (None = unassigned leads)
            force: Kept for API compatibility; eligibility no longer varies by force.
            
        Returns:
            Count of eligible leads
        """
        where_clauses = [
            "(dnc_flag = 0 OR dnc_flag IS NULL)"
        ]
        params = []
        
        # ⚠️ CRITICAL: Only allow leads that have never been sent consent SMS or were sent > cooldown days ago.
        # Do not select leads already sent within cooldown (avoids duplicate SMS and matches campaign creation).
        cooldown_days = config.campaign.SMS_CONSENT_COOLDOWN_DAYS
        where_clauses.append(
            f"(sms_consent_requested_at IS NULL OR sms_consent_requested_at < DATEADD(day, -{cooldown_days}, GETDATE()))"
        )
        
        if store_id is not None:
            where_clauses.append("store_id = ?")
            params.append(store_id)
        else:
            # Count unassigned leads
            where_clauses.append("store_id IS NULL")
        
        where_sql = "WHERE " + " AND ".join(where_clauses)
        
        # Exclude leads already in a progressing campaign.
        # sms_batches.status is defined in core/schema.py: 'pending', 'executing', 'completed', 'failed'
        # In-progress = pending (scheduled) or executing (sending now)
        where_sql += """
            AND NOT EXISTS (
                SELECT 1
                FROM batch_lead_mapping blm
                INNER JOIN sms_batches b ON blm.batch_id = b.batch_id
                WHERE blm.lead_id = OutboundLeads.lead_id
                  AND b.status IN ('pending', 'executing')
            )
        """
        
        query = f"""
            SELECT COUNT(*)
            FROM OutboundLeads
            {where_sql}
        """
        
        result = self.execute_scalar(query, tuple(params) if params else None)
        return result or 0
    
    def get_eligible_for_consent(
        self,
        limit: int = 100,
        store_id: Optional[int] = None,
        force: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get leads eligible for consent SMS requests.
        
        Eligibility criteria (matching campaign logic):
        - dnc_flag = 0
        - Never sent consent SMS, or consent sent more than cooldown days ago
        - Not already in a progressing campaign (batch status pending or executing)
        - store_id matches (if provided)
        
        Args:
            limit: Maximum number of leads to return
            store_id: Filter by store ID (None = unassigned leads only, matches count_eligible_for_consent)
            force: Kept for API compatibility; eligibility no longer varies by force.
            
        Returns:
            List of lead dictionaries ordered by priority, then created_at
        """
        where_clauses = [
            "(dnc_flag = 0 OR dnc_flag IS NULL)"
        ]
        params = []
        
        # ⚠️ CRITICAL: Only allow leads that have never been sent consent SMS or were sent > cooldown days ago.
        cooldown_days = config.campaign.SMS_CONSENT_COOLDOWN_DAYS
        where_clauses.append(
            f"(sms_consent_requested_at IS NULL OR sms_consent_requested_at < DATEADD(day, -{cooldown_days}, GETDATE()))"
        )
        
        if store_id is not None:
            where_clauses.append("store_id = ?")
            params.append(store_id)
        else:
            # None = unassigned leads only (matches count_eligible_for_consent(store_id=None))
            where_clauses.append("store_id IS NULL")
        
        where_sql = "WHERE " + " AND ".join(where_clauses)
        
        # Exclude leads already in a progressing campaign (see core/schema.py for batch status values)
        where_sql += """
            AND NOT EXISTS (
                SELECT 1
                FROM batch_lead_mapping blm
                INNER JOIN sms_batches b ON blm.batch_id = b.batch_id
                WHERE blm.lead_id = OutboundLeads.lead_id
                  AND b.status IN ('pending', 'executing')
            )
        """
        
        query = f"""
            SELECT TOP {limit}
                lead_id, name, Address, City, County, State, Zip, phone_number,
                priority, call_count, dnc_flag, sms_verified, sms_verified_at,
                sms_consent_requested_at, created_at, last_called, store_id
            FROM OutboundLeads
            {where_sql}
            ORDER BY 
                CASE WHEN priority IS NOT NULL THEN priority ELSE 999 END ASC,
                created_at ASC
        """
        
        rows = self.execute_query(query, tuple(params) if params else None, fetch_all=True)
        return [self._row_to_dict(row) for row in rows]
    
    def _row_to_dict(self, row) -> Dict[str, Any]:
        """Convert database row to dictionary."""
        if not row:
            return None
        
        # Handle both 17-column (without sms_from_number) and 18-column (with sms_from_number) rows
        # for backward compatibility during migration
        row_length = len(row)
        
        result = {
            "lead_id": row[0],
            "name": row[1],
            "Address": row[2],
            "City": row[3],
            "County": row[4],
            "State": row[5],
            "Zip": row[6],
            "phone_number": row[7],
            "priority": row[8],
            "call_count": row[9],
            "dnc_flag": bool(row[10]) if row[10] is not None else False,
            # SQL Server BIT type returns as int (0 or 1), convert to bool
            "sms_verified": bool(row[11]) if row[11] is not None else False,
            "sms_verified_at": row[12].isoformat() if row[12] else None,
            "sms_consent_requested_at": row[13].isoformat() if row[13] else None,
            "created_at": row[14].isoformat() if row[14] else None,
            "last_called": row[15].isoformat() if row[15] else None,
            "store_id": row[16]
        }
        
        # Add sms_from_number if present (18th column)
        if row_length > 17:
            result["sms_from_number"] = row[17]
        else:
            result["sms_from_number"] = None
        
        return result

