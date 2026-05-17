"""
Popup Repository
Handles all database operations for popup queue.
"""

from typing import Optional, List, Dict, Any
from .base import BaseRepository


class PopupRepository(BaseRepository):
    """Repository for popup queue data access."""
    
    def get_pending_popups(
        self,
        limit: int = 50,
        offset: int = 0,
        sort_field: Optional[str] = None,
        sort_direction: Optional[str] = None,
        priority: Optional[int] = None
    ) -> tuple[List[Dict[str, Any]], int]:
        """Get pending popup notifications with pagination and sorting."""
        limit = max(1, min(limit, 200))
        offset = max(0, offset)
        
        sort_field = (sort_field or "created_at").lower()
        sort_direction = (sort_direction or "asc").lower()
        
        sort_columns = {
            "created_at": "pq.created_at",
            "priority": "l.priority",
            "name": "l.name",
        }
        order_column = sort_columns.get(sort_field, "pq.created_at")
        order_direction = "ASC" if sort_direction == "asc" else "DESC"
        
        # Get total count
        count_query = """
            SELECT COUNT(*)
            FROM PopupQueue pq
            INNER JOIN OutboundLeads l ON pq.lead_id = l.lead_id
            WHERE pq.status = 'pending'
        """
        count_params = []
        
        if priority is not None:
            count_query += " AND l.priority = ?"
            count_params.append(priority)
        
        total_pending = self.execute_scalar(count_query, tuple(count_params) if count_params else None) or 0
        
        # Get popups with pagination
        query = f"""
            SELECT 
                pq.popup_id,
                pq.lead_id,
                pq.status,
                pq.created_at,
                l.name,
                l.phone_number,
                l.Address,
                l.City,
                l.State,
                l.priority,
                l.call_count,
                l.dnc_flag,
                l.sms_verified,
                l.sms_verified_at,
                l.sms_consent_requested_at
            FROM PopupQueue pq
            INNER JOIN OutboundLeads l ON pq.lead_id = l.lead_id
            WHERE pq.status = 'pending'
        """
        
        params = []
        
        if priority is not None:
            query += " AND l.priority = ?"
            params.append(priority)
        
        query += f" ORDER BY {order_column} {order_direction}, pq.popup_id ASC"
        query += " OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
        params.extend([offset, limit])
        
        rows = self.execute_query(query, tuple(params), fetch_all=True)
        
        popups = []
        for row in rows:
            popups.append({
                'popup_id': row[0],
                'lead_id': row[1],
                'status': row[2],
                'created_at': row[3].isoformat() if row[3] else None,
                'lead': {
                    'lead_id': row[1],
                    'name': row[4],
                    'phone_number': row[5],
                    'Address': row[6],
                    'City': row[7],
                    'State': row[8],
                    'priority': row[9],
                    'call_count': row[10],
                    'dnc_flag': bool(row[11]),
                    'sms_verified': bool(row[12]),
                    'sms_verified_at': row[13].isoformat() if row[13] else None,
                    'sms_consent_requested_at': row[14].isoformat() if row[14] else None
                }
            })
        
        return popups, total_pending
    
    def dismiss_popup(self, popup_id: int) -> bool:
        """Dismiss a popup notification."""
        query = """
            UPDATE PopupQueue
            SET status = 'dismissed',
                dismissed_at = GETDATE()
            WHERE popup_id = ?
        """
        rows_affected = self.execute_non_query(query, (popup_id,))
        return rows_affected > 0
    
    def mark_as_dialed(self, lead_id: int, employee_name: str) -> bool:
        """Mark popup as dialed."""
        query = """
            UPDATE PopupQueue 
            SET status = 'dialed', 
                dialed_at = GETDATE(),
                dialed_by = ?
            WHERE lead_id = ? AND status = 'pending'
        """
        rows_affected = self.execute_non_query(query, (employee_name, lead_id))
        return rows_affected > 0
    
    def update_call_sid(self, popup_id: int, call_sid: str) -> bool:
        """Update popup with call SID."""
        query = """
            UPDATE PopupQueue 
            SET call_sid = ?
            WHERE popup_id = ?
        """
        rows_affected = self.execute_non_query(query, (call_sid, popup_id))
        return rows_affected > 0
    
    def create(self, lead_id: int) -> int:
        """Create a new popup entry."""
        query = """
            INSERT INTO PopupQueue (lead_id, status, created_at)
            VALUES (?, 'pending', GETDATE())
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(query, (lead_id,))
                return self.get_last_insert_id(conn)
            finally:
                cursor.close()


