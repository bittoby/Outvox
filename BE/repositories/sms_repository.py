"""
SMS Repository
Handles all database operations for SMS conversations and photo submissions.
"""

from typing import Optional, List, Dict, Any
from .base import BaseRepository


class SMSRepository(BaseRepository):
    """Repository for SMS data access."""
    
    def get_conversation_by_lead(self, lead_id: int) -> Dict[str, Any]:
        """Get SMS conversation for a specific lead with lead info."""
        # Get lead information
        lead_query = """
            SELECT lead_id, name, Address, City, County, State, Zip, phone_number, 
                   priority, dnc_flag, created_at, last_called
            FROM OutboundLeads
            WHERE lead_id = ?
        """
        lead_row = self.execute_query(lead_query, (lead_id,), fetch_one=True)
        
        if not lead_row:
            return None
        
        lead_info = {
            "lead_id": lead_row[0],
            "name": lead_row[1],
            "address": lead_row[2],
            "city": lead_row[3],
            "county": lead_row[4],
            "state": lead_row[5],
            "zip": lead_row[6],
            "phone_number": lead_row[7],
            "priority": lead_row[8],
            "dnc_flag": bool(lead_row[9]),
            "created_at": lead_row[10].isoformat() if lead_row[10] else None,
            "last_called": lead_row[11].isoformat() if lead_row[11] else None
        }
        
        # Get SMS conversations
        sms_query = """
            SELECT sms_id, message_type, message_content, direction, created_at, twilio_sid
            FROM SMSConversations
            WHERE lead_id = ?
            ORDER BY created_at ASC
        """
        rows = self.execute_query(sms_query, (lead_id,), fetch_all=True)
        
        conversations = []
        for row in rows:
            conversations.append({
                "sms_id": row[0],
                "message_type": row[1],
                "message_content": row[2],
                "direction": row[3],
                "created_at": row[4].isoformat() if row[4] else None,
                "twilio_sid": row[5]
            })
        
        return {
            "lead_info": lead_info,
            "conversations": conversations,
            "total_messages": len(conversations)
        }
    
    def get_conversation_by_phone(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """
        Get SMS conversation by phone number (for conversations without lead_id).
        
        Args:
            phone_number: Phone number in E.164 format
            
        Returns:
            Dict with conversations and phone info, or None if not found
        """
        # Normalize phone number
        from utils.phone_validator import normalize_phone_number
        normalized_phone = normalize_phone_number(phone_number)
        
        if not normalized_phone:
            return None
        
        # Get SMS conversations by phone number (where lead_id is NULL)
        sms_query = """
            SELECT sms_id, message_type, message_content, direction, created_at, twilio_sid, phone_number
            FROM SMSConversations
            WHERE phone_number = ? AND lead_id IS NULL
            ORDER BY created_at ASC
        """
        rows = self.execute_query(sms_query, (normalized_phone,), fetch_all=True)
        
        if not rows:
            return None
        
        conversations = []
        for row in rows:
            conversations.append({
                "sms_id": row[0],
                "message_type": row[1],
                "message_content": row[2],
                "direction": row[3],
                "created_at": row[4].isoformat() if row[4] else None,
                "twilio_sid": row[5]
            })
        
        # Return minimal lead_info (just phone number) since no lead exists
        return {
            "lead_info": {
                "lead_id": None,
                "name": None,
                "address": None,
                "city": None,
                "county": None,
                "state": None,
                "zip": None,
                "phone_number": normalized_phone,
                "priority": None,
                "dnc_flag": False,
                "created_at": None,
                "last_called": None
            },
            "conversations": conversations,
            "total_messages": len(conversations)
        }
    
    def get_all_conversations(
        self,
        limit: int = 100,
        offset: int = 0,
        direction: Optional[str] = None,
        store_id: Optional[int] = None
    ) -> tuple[List[Dict[str, Any]], int]:
        """Get all SMS conversations with optional filtering."""
        where_conditions = []
        params = []
        
        if direction and direction in ['inbound', 'outbound']:
            where_conditions.append("s.direction = ?")
            params.append(direction)
        
        if store_id is not None:
            where_conditions.append("l.store_id = ?")
            params.append(store_id)
        
        where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        query = f"""
            SELECT 
                s.sms_id,
                s.lead_id,
                s.message_type,
                s.message_content,
                s.direction,
                s.created_at,
                s.twilio_sid,
                l.name as lead_name,
                COALESCE(l.phone_number, s.phone_number) as phone_number,
                l.City,
                l.State,
                l.Address,
                l.store_id,
                st.name as store_name
            FROM SMSConversations s
            LEFT JOIN OutboundLeads l ON s.lead_id = l.lead_id
            LEFT JOIN stores st ON l.store_id = st.store_id
            {where_clause}
            ORDER BY s.created_at DESC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """
        
        params.extend([offset, limit])
        rows = self.execute_query(query, tuple(params), fetch_all=True)
        
        conversations = []
        for row in rows:
            conversations.append({
                "sms_id": row[0],
                "lead_id": row[1],
                "message_type": row[2],
                "message_content": row[3],
                "direction": row[4],
                "created_at": row[5].isoformat() if row[5] else None,
                "twilio_sid": row[6],
                "lead_name": row[7],
                "phone_number": row[8],
                "city": row[9],
                "state": row[10],
                "address": row[11],
                "store_id": row[12],
                "store_name": row[13]
            })
        
        # Get total count
        count_query = f"""
            SELECT COUNT(*)
            FROM SMSConversations s
            LEFT JOIN OutboundLeads l ON s.lead_id = l.lead_id
            {where_clause}
        """
        count_params = params[:-2]  # Remove offset and limit
        total_count = self.execute_scalar(count_query, tuple(count_params) if count_params else None) or 0
        
        return conversations, total_count
    
    def delete_conversation_by_lead(self, lead_id: int) -> int:
        """Delete all SMS conversations for a specific lead."""
        query = "DELETE FROM SMSConversations WHERE lead_id = ?"
        rows_affected = self.execute_non_query(query, (lead_id,))
        return rows_affected
    
    def delete_all_conversations(self) -> int:
        """Delete all SMS conversations."""
        query = "DELETE FROM SMSConversations"
        rows_affected = self.execute_non_query(query)
        return rows_affected
    
    def get_all_photo_submissions(
        self,
        limit: int = 100,
        offset: int = 0,
        status: Optional[str] = None
    ) -> tuple[List[Dict[str, Any]], int]:
        """Get all photo submissions with optional status filter."""
        where_conditions = []
        params = []
        
        if status and status in ['pending', 'reviewed', 'appraised']:
            where_conditions.append("p.status = ?")
            params.append(status)
        
        where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        query = f"""
            SELECT 
                p.photo_id,
                p.lead_id,
                p.phone_number,
                p.photo_url,
                p.status,
                p.created_at,
                p.reviewed_at,
                p.reviewed_by,
                l.name as lead_name,
                l.Address,
                l.City,
                l.State
            FROM PhotoSubmissions p
            INNER JOIN OutboundLeads l ON p.lead_id = l.lead_id
            {where_clause}
            ORDER BY p.created_at DESC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """
        
        params.extend([offset, limit])
        rows = self.execute_query(query, tuple(params), fetch_all=True)
        
        photos = []
        for row in rows:
            photos.append({
                "photo_id": row[0],
                "lead_id": row[1],
                "phone_number": row[2],
                "photo_url": row[3],
                "status": row[4],
                "created_at": row[5].isoformat() if row[5] else None,
                "reviewed_at": row[6].isoformat() if row[6] else None,
                "reviewed_by": row[7],
                "lead_name": row[8],
                "address": row[9],
                "city": row[10],
                "state": row[11]
            })
        
        # Get total count
        count_query = f"""
            SELECT COUNT(*)
            FROM PhotoSubmissions p
            {where_clause}
        """
        count_params = params[:-2]  # Remove offset and limit
        total_count = self.execute_scalar(count_query, tuple(count_params) if count_params else None) or 0
        
        return photos, total_count
    
    def delete_photo_submission(self, photo_id: int) -> bool:
        """Delete a photo submission."""
        query = "DELETE FROM PhotoSubmissions WHERE photo_id = ?"
        rows_affected = self.execute_non_query(query, (photo_id,))
        return rows_affected > 0
    
    def delete_all_photos(self) -> int:
        """Delete all photo submissions."""
        query = "DELETE FROM PhotoSubmissions"
        rows_affected = self.execute_non_query(query)
        return rows_affected
    
    def create_sms_conversation(
        self,
        lead_id: int,
        phone_number: str,
        message_type: str,
        message_content: str,
        twilio_sid: Optional[str],
        direction: str = 'outbound'
    ) -> int:
        """Create a new SMS conversation entry."""
        query = """
            INSERT INTO SMSConversations (lead_id, phone_number, message_type, message_content, twilio_sid, direction)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(query, (lead_id, phone_number, message_type, message_content, twilio_sid, direction))
                return self.get_last_insert_id(conn)
            finally:
                cursor.close()
    
    def create_photo_submission(
        self,
        lead_id: int,
        phone_number: str,
        photo_url: str,
        status: str = 'pending'
    ) -> int:
        """Create a new photo submission."""
        query = """
            INSERT INTO PhotoSubmissions (lead_id, phone_number, photo_url, status)
            VALUES (?, ?, ?, ?)
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(query, (lead_id, phone_number, photo_url, status))
                return self.get_last_insert_id(conn)
            finally:
                cursor.close()
    
    def get_pending_photos(self) -> List[Dict[str, Any]]:
        """Get all pending photo submissions with lead info."""
        query = """
            SELECT 
                p.photo_id, p.lead_id, p.phone_number, p.photo_url, p.created_at, l.name
            FROM PhotoSubmissions p
            JOIN OutboundLeads l ON p.lead_id = l.lead_id
            WHERE p.status = 'pending'
            ORDER BY p.created_at ASC
        """
        rows = self.execute_query(query, fetch_all=True)
        
        photos = []
        for row in rows:
            photos.append({
                'photo_id': row[0],
                'lead_id': row[1],
                'phone_number': row[2],
                'photo_url': row[3],
                'created_at': row[4].isoformat() if row[4] else None,
                'customer_name': row[5]
            })
        
        return photos
    
    def update_photo_status(
        self,
        photo_id: int,
        status: str,
        reviewed_by: Optional[str] = None
    ) -> bool:
        """Update photo submission status."""
        query = """
            UPDATE PhotoSubmissions 
            SET status = ?, reviewed_at = GETDATE(), reviewed_by = ?
            WHERE photo_id = ?
        """
        rows_affected = self.execute_non_query(query, (status, reviewed_by, photo_id))
        return rows_affected > 0


