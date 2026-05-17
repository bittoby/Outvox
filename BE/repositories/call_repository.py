"""
Call Repository
Handles all database operations for call results.
"""

from typing import Optional, List, Dict, Any
from .base import BaseRepository


class CallRepository(BaseRepository):
    """Repository for call data access."""
    
    def get_call_history(
        self,
        limit: int = 100,
        offset: int = 0,
        result_type: Optional[str] = None,
        store_id: Optional[int] = None
    ) -> tuple[List[Dict[str, Any]], int]:
        """Get call history with pagination and filtering."""
        limit = max(1, min(limit, 500))
        offset = max(0, offset)
        
        where_clauses = []
        params = []
        
        if result_type:
            where_clauses.append("r.result_type = ?")
            params.append(result_type)
        
        if store_id is not None:
            where_clauses.append("l.store_id = ?")
            params.append(store_id)
        
        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)
        
        query = f"""
            SELECT 
                r.result_id,
                r.lead_id,
                l.name as lead_name,
                l.phone_number as lead_phone,
                r.agent_id,
                r.twilio_number,
                r.call_sid,
                r.call_duration,
                r.result_type,
                r.customer_transcript,
                r.agent_transcript,
                r.combined_transcript,
                r.created_at,
                l.store_id,
                s.name as store_name
            FROM OutboundCallResults r
            INNER JOIN OutboundLeads l ON r.lead_id = l.lead_id
            LEFT JOIN stores s ON l.store_id = s.store_id
            {where_sql}
            ORDER BY r.created_at DESC
            OFFSET ? ROWS
            FETCH NEXT ? ROWS ONLY
        """
        
        params.extend([offset, limit])
        rows = self.execute_query(query, tuple(params), fetch_all=True)
        
        calls = []
        for row in rows:
            calls.append({
                "result_id": row[0],
                "lead_id": row[1],
                "lead_name": row[2],
                "lead_phone": row[3],
                "agent_id": row[4],
                "twilio_number": row[5],
                "call_sid": row[6],
                "call_duration": row[7],
                "result_type": row[8],
                "customer_transcript": row[9],
                "agent_transcript": row[10],
                "combined_transcript": row[11],
                "created_at": row[12].isoformat() if row[12] else None,
                "store_id": row[13],
                "store_name": row[14]
            })
        
        # Get total count
        count_params = params[:-2]
        count_query = f"""
            SELECT COUNT(*) as total
            FROM OutboundCallResults r
            INNER JOIN OutboundLeads l ON r.lead_id = l.lead_id
            {where_sql}
        """
        total = self.execute_scalar(count_query, tuple(count_params) if count_params else None) or 0
        
        return calls, total
    
    def get_call_by_id(self, result_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific call."""
        query = """
            SELECT 
                r.result_id,
                r.lead_id,
                l.name as lead_name,
                l.phone_number as lead_phone,
                l.Address,
                l.City,
                l.County,
                l.State,
                l.Zip,
                r.agent_id,
                r.twilio_number,
                r.call_sid,
                r.call_duration,
                r.result_type,
                r.customer_transcript,
                r.agent_transcript,
                r.combined_transcript,
                r.created_at,
                l.store_id,
                s.name as store_name
            FROM OutboundCallResults r
            INNER JOIN OutboundLeads l ON r.lead_id = l.lead_id
            LEFT JOIN stores s ON l.store_id = s.store_id
            WHERE r.result_id = ?
        """
        row = self.execute_query(query, (result_id,), fetch_one=True)
        
        if not row:
            return None
        
        return {
            "result_id": row[0],
            "lead_id": row[1],
            "lead_name": row[2],
            "lead_phone": row[3],
            "lead_address": row[4],
            "lead_city": row[5],
            "lead_county": row[6],
            "lead_state": row[7],
            "lead_zip": row[8],
            "agent_id": row[9],
            "twilio_number": row[10],
            "call_sid": row[11],
            "call_duration": row[12],
            "result_type": row[13],
            "customer_transcript": row[14],
            "agent_transcript": row[15],
            "combined_transcript": row[16],
            "created_at": row[17].isoformat() if row[17] else None,
            "store_id": row[18],
            "store_name": row[19]
        }
    
    def create_call_result(self, call_data: Dict[str, Any]) -> int:
        """Create a new call result record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO OutboundCallResults 
                    (lead_id, agent_id, twilio_number, call_sid, call_duration,
                     result_type, customer_transcript, agent_transcript, combined_transcript)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    call_data.get('lead_id'),
                    call_data.get('agent_id'),
                    call_data.get('twilio_number'),
                    call_data.get('call_sid'),
                    call_data.get('call_duration'),
                    call_data.get('result_type'),
                    call_data.get('customer_transcript'),
                    call_data.get('agent_transcript'),
                    call_data.get('combined_transcript', '')
                ))
                
                return self.get_last_insert_id(conn)
            finally:
                cursor.close()
    
    def update_lead_after_call(
        self,
        lead_id: int,
        result_type: str,
        is_dnc: bool = False
    ) -> bool:
        """Update lead after call (increment call_count, update last_called, set DNC if needed)."""
        set_clauses = [
            "call_count = ISNULL(call_count, 0) + 1",
            "last_called = GETDATE()"
        ]
        params = []
        
        if is_dnc:
            set_clauses.append("dnc_flag = 1")
        
        params.append(lead_id)
        query = f"UPDATE OutboundLeads SET {', '.join(set_clauses)} WHERE lead_id = ?"
        
        rows_affected = self.execute_non_query(query, tuple(params))
        return rows_affected > 0
    
    def delete_call_result(self, result_id: int) -> bool:
        """Delete a call result record."""
        query = "DELETE FROM OutboundCallResults WHERE result_id = ?"
        rows_affected = self.execute_non_query(query, (result_id,))
        return rows_affected > 0


